"""Synthetic offline checks; no production context, student data or API credentials."""
import asyncio
import importlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import redirect_stdout

from pydantic import ValidationError
from mentoring.models import MentorInsight, ParsedMentoringSession
from mentoring.services import mentor_context as store
from mentoring.services.mentor_insights import validate_insights, insight_summary, plain_rich_text

QUOTE = 'AI 답변의 출처를 확인할 수 없어 결과를 신뢰하기 어려웠습니다.'


def sample_context():
    return store.MentorContext(enabled=True, services=[
        {'id': 'svc-sample', 'name': '테스트 지식검색', 'details': '내부 문서 검색 AI, 신뢰와 출처 검증', 'approved': True},
        {'id': 'svc-private', 'name': '비승인 서비스', 'details': '전송하면 안 되는 정보', 'approved': False},
    ], notes=[{'id': 'ctx-reviewed', 'title': '검토한 메모', 'text': '출처 정확도를 검증하고 싶다.', 'approved': True},
              {'id': 'ctx-private', 'title': '비승인 메모', 'text': '절대 전달하지 않을 테스트 문자열', 'approved': False}])


def sample_insight(**overrides):
    data = dict(insightTitle='출처 검증 경험 실험', insightType='기획 실무',
                description=['출처를 확인할 수 있는 경험이 필요한지 검증한다.'],
                insightKind='업무 적용 가설', evidenceQuotes=[QUOTE], targetServiceId='svc-sample',
                contextRefs=['ctx-reviewed'], applicability='검색 결과의 근거 확인 문제와 연결된다.',
                nextExperiment='출처 표시 프로토타입으로 확인 과제를 수행한다.',
                successCriterion='사용자의 근거 확인 성공 여부와 소요 시간을 비교한다.',
                caveats='한 사례이며 실제 서비스 사용자에게 같은 문제가 있는지 검증해야 한다.')
    data.update(overrides)
    return MentorInsight(**data)


class MentorInsightTests(unittest.TestCase):
    def setUp(self):
        output = redirect_stdout(io.StringIO())
        output.__enter__(); self.addCleanup(output.__exit__, None, None, None)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'runtime' / 'mentor_context.json'
        patcher = patch.object(store, 'CONTEXT_FILE', self.path)
        patcher.start(); self.addCleanup(patcher.stop)

    def web(self):
        with patch('mentoring.config.load_environment'):
            return importlib.import_module('mentoring.web.app').app.test_client()

    def test_default_and_disabled_context_never_forward_work_data(self):
        self.assertEqual(store.approved_context(), {})
        context = sample_context(); context.enabled = False
        store.save_context(context.model_dump())
        self.assertEqual(store.approved_context(), {})

    def test_only_reviewed_items_are_forwarded_and_roundtrip_preserves_drafts(self):
        saved = store.save_context(sample_context().model_dump())
        self.assertTrue(saved.revision)
        preview = json.dumps(store.approved_context(), ensure_ascii=False)
        self.assertIn('테스트 지식검색', preview)
        self.assertNotIn('비승인', preview)
        self.assertNotIn('절대 전달하지', preview)
        self.assertEqual(len(store.load_context().notes), 2)

    def test_stale_writes_cannot_overwrite_new_context(self):
        store.save_context(sample_context().model_dump())
        with self.assertRaises(store.ContextConflict):
            store.save_context(sample_context().model_dump())

    def test_invalid_context_does_not_replace_saved_file(self):
        saved = store.save_context(sample_context().model_dump())
        data = saved.model_dump(); data['notes'][0]['text'] = 'x' * 12001
        with self.assertRaises(ValidationError):
            store.save_context(data)
        self.assertEqual(store.load_context(), saved)
        data = saved.model_dump(); data['services'].append(data['services'][0])
        with self.assertRaises(ValidationError):
            store.save_context(data)

    def test_corrupt_file_fails_closed_without_disclosing_contents(self):
        self.path.parent.mkdir(); self.path.write_text('private broken data', encoding='utf-8')
        self.assertEqual(store.approved_context(), {})
        response = self.web().get('/api/mentor-context')
        self.assertEqual(response.status_code, 400)
        self.assertNotIn('private broken data', response.get_data(as_text=True))

    def test_local_api_save_preview_delete_without_model_calls(self):
        client = self.web()
        with patch('google.genai.Client', side_effect=AssertionError('No LLM calls during settings edits')):
            result = client.put('/api/mentor-context', json=sample_context().model_dump())
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.headers['Cache-Control'], 'no-store')
            body = result.get_json()
            self.assertEqual(len(body['preview']['services']), 1)
            stale = client.put('/api/mentor-context', json=sample_context().model_dump())
            self.assertEqual(stale.status_code, 409)
            deleted = client.delete('/api/mentor-context', json={'revision': body['data']['revision']})
            self.assertEqual(deleted.status_code, 200)
            self.assertFalse(self.path.exists())

    def test_cross_origin_and_malformed_requests_rejected(self):
        client = self.web()
        result = client.put('/api/mentor-context', json={}, headers={'Origin': 'https://other.example'})
        self.assertEqual(result.status_code, 403)
        self.assertEqual(client.put('/api/mentor-context', data='{}').status_code, 415)
        self.assertEqual(client.put('/api/mentor-context', json=[]).status_code, 400)
        self.assertFalse(self.path.exists())

    def test_valid_hypothesis_resolves_service_and_context_version(self):
        context = store.approved_context(sample_context()); context['revision'] = 'example-version'
        result = validate_insights([sample_insight()], QUOTE, context)
        self.assertEqual(result[0].targetService, '테스트 지식검색')
        self.assertIn('svc-sample', result[0].contextRefs)
        self.assertEqual(result[0].mentorContextVersion, 'example-version')

    def test_invented_quote_service_or_unapproved_reference_dropped(self):
        context = store.approved_context(sample_context())
        for item in [sample_insight(evidenceQuotes=['원문에 등장하지 않는 문장입니다.']),
                     sample_insight(targetServiceId='svc-invented'),
                     sample_insight(contextRefs=['ctx-private']), sample_insight(nextExperiment='')]:
            self.assertEqual(validate_insights([item], QUOTE, context), [])

    def test_generic_hypothesis_when_context_is_disabled_is_labelled(self):
        item = sample_insight(targetServiceId='', contextRefs=[])
        result = validate_insights([item], QUOTE, {})
        self.assertEqual(result[0].targetService, '')
        self.assertIn('일반 제안', result[0].caveats)

    def test_notion_format_preserves_long_text_without_new_db_fields(self):
        item = sample_insight(description=['x' * 5000])
        text = insight_summary(item)
        rich = plain_rich_text(text)
        self.assertEqual(''.join(t['text']['content'] for t in rich), text)
        self.assertTrue(all(len(t['text']['content']) <= 1900 for t in rich))
        from mentoring.services.upsert import NotionUpsertHandler
        api = MagicMock(create_page=AsyncMock())
        asyncio.run(NotionUpsertHandler(api)._insert_insights('db', [item], 'student', 'session'))
        properties = api.create_page.call_args.args[1]
        self.assertEqual(set(properties), {'Insight Title', 'Insight Type', 'Summary', '🧑‍🎓 Students (학생 CRM)', '💬 Mentoring Sessions'})

    def test_legacy_insight_schema_still_loads(self):
        item = MentorInsight(insightTitle='이전 항목', insightType='교육 개선', description=['기존 내용'])
        self.assertIn('기존 내용', insight_summary(item))

    def test_all_categories_and_all_rich_text_pages_reach_retrospective(self):
        from mentoring.services.summarize_insights import fetch_insights
        row = {'id': 'example-id', 'properties': {'Insight Title': {'title': [{'plain_text': '교육 개선'}]},
               'Summary': {'rich_text': [{'plain_text': '첫 조각'}, {'plain_text': '둘째 조각'}]},
               'Insight Type': {'select': {'name': '교육 개선'}}}}
        api = MagicMock(query_database=AsyncMock(side_effect=[{'results': [row], 'has_more': True, 'next_cursor': 'next'},
                                                             {'results': [row], 'has_more': False}]))
        results = asyncio.run(fetch_insights(api, 'example-db'))
        self.assertEqual(len(results), 2)
        self.assertIn('첫 조각둘째 조각', results[0])
        self.assertNotIn('filter_payload', api.query_database.call_args_list[0].kwargs)
        self.assertEqual(api.query_database.call_args_list[1].kwargs['start_cursor'], 'next')

    def test_parser_receives_approved_context_and_checks_real_quotes(self):
        from mentoring.services.llm_parser import LLMParser
        brief = dict(backgroundContext=[], trafficLightStatus='🟢 정상 진행', warningSignals=[],
                     pastAssignmentStatus='확인 필요', discussionPoints=[QUOTE], oneSentenceSummary=QUOTE, actionItems=[])
        session = ParsedMentoringSession(sessionDate='2026-08-30', sessionNumber=1,
            routing=dict(matchedCourse='Sample', matchedStudent='Sample', confidence=1, matchingReason='sample', needsHumanReview=False),
            mentorBrief=brief, assignmentTitle=None, submissionStatus='Not Started', mentorInsights=[sample_insight()])
        store.save_context(sample_context().model_dump())
        parser = object.__new__(LLMParser)
        parser.client = MagicMock()
        parser.client.models.generate_content.return_value.text = session.model_dump_json()
        result = asyncio.run(parser.parse_mentoring_data(QUOTE, 'sample', 'Sample', 'Sample', []))
        prompt = parser.client.models.generate_content.call_args.kwargs['contents']
        self.assertIn('테스트 지식검색', prompt)
        self.assertNotIn('절대 전달하지', prompt)
        self.assertIn('업무 적용 가설', prompt)
        self.assertEqual(result.mentorInsights[0].targetService, '테스트 지식검색')

    def test_summary_prompt_distinguishes_facts_and_hypotheses(self):
        from mentoring.services.summarize_insights import generate_retrospective
        with patch('mentoring.services.summarize_insights.genai.Client') as client:
            client.return_value.models.generate_content.return_value.text = 'synthetic report'
            result = asyncio.run(generate_retrospective(['근거 ID: sample\n테스트 근거']))
            prompt = client.return_value.models.generate_content.call_args.kwargs['contents']
            self.assertIn('원문 근거 확인 필요', prompt)
            self.assertIn('작은 실험', prompt)
            self.assertIn('업무 맥락 사용 꺼짐', prompt)
            self.assertEqual(result, 'synthetic report')


if __name__ == '__main__':
    unittest.main()
