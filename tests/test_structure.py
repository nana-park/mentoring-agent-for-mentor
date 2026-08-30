"""Offline regression tests for the package move; external writes are forbidden."""
import ast
import asyncio
import importlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import AsyncMock, MagicMock, patch

from mentoring import config


class StructureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.previous_cwd = Path.cwd()
        os.chdir(self.tmp.name)
        self.addCleanup(os.chdir, self.previous_cwd)
        # Do not allow a test to accidentally reach an external API.
        original_connect = socket.socket.connect
        def local_only(sock, address):
            # Windows asyncio uses a loopback socketpair internally.
            if isinstance(address, tuple) and address[0] in ('127.0.0.1', '::1'):
                return original_connect(sock, address)
            raise AssertionError('External network forbidden')
        self.network = patch.object(socket.socket, 'connect', new=local_only)
        self.network.start()
        self.addCleanup(self.network.stop)

    def web(self):
        with patch('mentoring.config.load_environment'):
            return importlib.import_module('mentoring.web.app')

    def test_active_python_sources_parse(self):
        files = list(config.PROJECT_ROOT.glob('*.py'))
        for folder in ['mentoring', 'scripts', 'tests']:
            files.extend((config.PROJECT_ROOT / folder).rglob('*.py'))
        for path in files:
            with self.subTest(file=str(path.relative_to(config.PROJECT_ROOT))):
                ast.parse(path.read_text(encoding='utf-8-sig'))

    def test_paths_stay_at_project_root_from_other_cwd(self):
        expected = {
            'ENV_FILE': '.env', 'DB_CONFIG_FILE': 'db_config.json',
            'AUTOMATION_CONFIG_FILE': 'automation_config.json',
            'GOOGLE_TOKEN_FILE': 'token.json', 'GOOGLE_CREDENTIALS_FILE': 'credentials.json',
            'INBOX_DIR': 'inbox', 'ARCHIVE_DIR': 'archive', 'DOCS_DIR': 'docs',
        }
        for key, relative in expected.items():
            self.assertEqual(getattr(config, key), config.PROJECT_ROOT / relative)
        with patch('mentoring.config.load_dotenv') as dotenv:
            config.load_environment()
            dotenv.assert_called_once_with(config.PROJECT_ROOT / '.env', override=False)

    def test_dashboard_assets_and_document_links_from_other_cwd(self):
        web = self.web()
        client = web.app.test_client()
        home = client.get('/')
        self.assertEqual(home.status_code, 200)
        self.assertIn(b'project_structure.md', home.data)
        for path in (config.WEB_DIR / 'static').rglob('*'):
            if path.is_file():
                response = client.get('/static/' + path.relative_to(config.WEB_DIR / 'static').as_posix())
                self.assertEqual(response.status_code, 200)
                response.close()
        for filename in ['architecture_diagram.md', 'database_schema.md', 'project_structure.md', 'mentor_insights.md']:
            data = client.get('/api/docs/' + filename).get_json()
            self.assertTrue(data['success'])
            self.assertEqual(data['content'], (config.DOCS_DIR / filename).read_text(encoding='utf-8'))
        self.assertFalse(client.get('/api/docs/.env').get_json()['success'])

    def test_cli_help_and_legacy_main_from_other_cwd(self):
        result = subprocess.run([sys.executable, str(config.PROJECT_ROOT / 'main.py'), '--help'],
                                cwd=self.tmp.name, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--payload', result.stdout)

    def test_cli_passes_explicit_payload_to_pipeline(self):
        from mentoring.cli import main
        with patch('mentoring.pipeline.run_pipeline', new_callable=AsyncMock) as pipeline:
            main(['--mode', 'direct', '--payload', 'session.json'])
            pipeline.assert_awaited_once_with('direct', payload='session.json')

    def test_launcher_commands_are_modules_and_do_not_wait_for_input(self):
        web = self.web()
        client = web.app.test_client()
        for mode in ['auto', 'batch', 'summarize']:
            with patch.object(web, 'stream_subprocess', return_value=iter(['data: {}\n\n'])) as stream:
                response = client.post('/api/run/' + mode)
                self.assertEqual(response.status_code, 200)
                response.get_data()
                args = stream.call_args.args[1]
                self.assertEqual(args[:3], [sys.executable, '-u', '-m'])
                self.assertIn('mentoring.services.summarize_insights' if mode == 'summarize' else 'mentoring.cli', args)

    def test_direct_payload_survives_command_and_is_cleaned_up(self):
        web = self.web()
        captured = {}
        def fake_stream(key, args, cleanup_file=None):
            captured['args'] = args
            captured['file'] = Path(cleanup_file)
            captured['payload'] = json.loads(captured['file'].read_text(encoding='utf-8'))
            try:
                yield 'data: {"success":true}\n\n'
            finally:
                captured['file'].unlink()
        payload = {'subject': 'Offline sample', 'students': [{'name': 'Sample', 'content': 'Example note'}]}
        with patch.object(web, 'stream_subprocess', side_effect=fake_stream):
            response = web.app.test_client().post('/api/run/direct', json=payload)
            response.get_data()
        self.assertEqual(captured['payload'], payload)
        self.assertEqual(captured['args'][-2:], ['--payload', str(captured['file'])])
        self.assertFalse(captured['file'].exists())

    def test_process_cwd_and_payload_cleanup(self):
        from mentoring.web import processes
        note = Path(self.tmp.name) / 'payload.json'
        note.write_text('{}', encoding='utf-8')
        proc = MagicMock()
        proc.stdout = io.StringIO('offline log\n')
        proc.returncode = 0
        with patch.object(processes.subprocess, 'Popen', return_value=proc) as popen:
            output = list(processes.stream_subprocess('offline-test', processes.pipeline_command('batch'), note))
        self.assertEqual(popen.call_args.kwargs['cwd'], config.PROJECT_ROOT)
        self.assertFalse(note.exists())
        self.assertNotIn('offline-test', processes.active_processes)
        self.assertIn('"success": true', output[-1])

    def test_scheduler_config_uses_explicit_file(self):
        from mentoring.web import scheduler
        path = Path(self.tmp.name) / 'automation.json'
        with patch.object(scheduler, 'CONFIG_FILE', path):
            self.assertFalse(scheduler.load_config()['enabled'])
            expected = {'enabled': False, 'time': '10:00', 'frequency': 'weekly', 'day': 'Monday'}
            scheduler.save_config(expected)
            self.assertEqual(scheduler.load_config(), expected)

    def test_google_credentials_paths_are_not_module_directory(self):
        google = importlib.import_module('mentoring.integrations.google_workspace')
        creds = MagicMock(valid=True)
        with patch.object(google.os.path, 'exists', return_value=True), \
             patch.object(google.Credentials, 'from_authorized_user_file', return_value=creds) as read_token:
            google.GoogleWorkspaceClient()
        read_token.assert_called_once_with(config.PROJECT_ROOT / 'token.json', google.SCOPES)
        self.assertEqual(google.GOOGLE_CREDENTIALS_FILE, config.PROJECT_ROOT / 'credentials.json')

    def test_batch_pipeline_keeps_existing_inbox_and_archive(self):
        from mentoring import pipeline
        ingestion = MagicMock()
        ingestion.load_active_courses = AsyncMock(return_value=[{'name': 'Sample', 'page_id': 'course', 'keyword': 'sample'}])
        ingestion.scan_course_dbs = AsyncMock(return_value={})
        upsert = MagicMock(sync_course_placeholders=AsyncMock())
        batch = MagicMock(fetch_unprocessed_files=MagicMock(return_value=[]))
        with patch.dict(os.environ, {'NOTION_TOKEN': 'offline-placeholder'}), \
             patch.object(pipeline, 'NotionAPIClient'), \
             patch.object(pipeline, 'DataIngestionLayer', return_value=ingestion), \
             patch.object(pipeline, 'LLMParser'), \
             patch.object(pipeline, 'NotionUpsertHandler', return_value=upsert), \
             patch.object(pipeline, 'BatchProcessor', return_value=batch) as processor, \
             patch('mentoring.config.load_environment'), redirect_stdout(io.StringIO()):
            asyncio.run(pipeline.run_pipeline('batch'))
        processor.assert_called_once_with(config.PROJECT_ROOT / 'inbox', config.PROJECT_ROOT / 'archive')

    def test_history_reads_root_config_without_network(self):
        web = self.web()
        path = Path(self.tmp.name) / 'db_config.json'
        path.write_text(json.dumps({'IngestionHistory': 'offline-history'}), encoding='utf-8')
        api = MagicMock(query_database=AsyncMock(return_value={'results': []}))
        with patch.object(web, 'DB_CONFIG_FILE', path), patch.object(web, 'NotionAPIClient', return_value=api):
            response = web.app.test_client().get('/api/history').get_json()
        self.assertTrue(response['success'])
        self.assertEqual(api.query_database.call_args.kwargs['database_id'], 'offline-history')

    def test_database_defaults_can_be_overridden_without_moving_files(self):
        with patch.dict(os.environ, {'NOTION_COURSES_DB_ID': 'sample-course', 'NOTION_REVIEW_QUEUE_ID': 'sample-review'}):
            self.assertEqual(config.course_database_id(), 'sample-course')
            self.assertEqual(config.review_queue_id(), 'sample-review')

    def test_active_modules_import_without_starting_services(self):
        with patch('mentoring.config.load_environment'), \
             patch('subprocess.Popen', side_effect=AssertionError('Unexpected subprocess')), \
             patch('threading.Thread.start', side_effect=AssertionError('Unexpected scheduler')):
            for folder in ['mentoring', 'scripts']:
                for path in (config.PROJECT_ROOT / folder).rglob('*.py'):
                    if path.name.startswith('__'):
                        continue
                    name = '.'.join(path.relative_to(config.PROJECT_ROOT).with_suffix('').parts)
                    with self.subTest(module=name):
                        importlib.import_module(name)

    def test_scheduler_starts_batch_module_from_root(self):
        from mentoring.web import scheduler
        now = scheduler.datetime.datetime(2026, 8, 30, 9, 0, 0)
        class EndIteration(BaseException):
            pass
        with patch.object(scheduler, 'load_config', return_value={'enabled': True, 'frequency': 'daily', 'time': '09:00'}), \
             patch.object(scheduler.datetime, 'datetime') as clock, \
             patch.object(scheduler.subprocess, 'Popen') as popen, \
             patch.object(scheduler.time, 'sleep', side_effect=EndIteration), \
             patch.dict(scheduler.active_processes, {}, clear=True), redirect_stdout(io.StringIO()):
            clock.now.return_value = now
            with self.assertRaises(EndIteration):
                scheduler.scheduler_loop()
            self.assertEqual(popen.call_args.args[0], [sys.executable, '-u', '-m', 'mentoring.cli', '--mode', 'batch'])
            self.assertEqual(popen.call_args.kwargs['cwd'], config.PROJECT_ROOT)


if __name__ == '__main__':
    unittest.main()
