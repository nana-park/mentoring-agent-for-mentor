"""Subprocess commands and streamed logs for the dashboard."""
import json
import os
import subprocess
import sys
from mentoring.config import PROJECT_ROOT

BASE_DIR = PROJECT_ROOT
active_processes = {}


def pipeline_command(mode, payload=None):
    args = [sys.executable, "-u", "-m", "mentoring.cli", "--mode", mode]
    if payload is not None:
        args.extend(["--payload", str(payload)])
    return args


def summarize_command():
    return [sys.executable, "-u", "-m", "mentoring.services.summarize_insights"]


def stream_subprocess(process_key, cmd_args, cleanup_file=None):
    if process_key in active_processes and active_processes[process_key].poll() is None:
        yield f"data: {json.dumps({'error': '이미 실행 중입니다.'})}\n\n"
        return

    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"

        proc = subprocess.Popen(
            cmd_args,
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            env=env,
            bufsize=1
        )
        active_processes[process_key] = proc

        for line in iter(proc.stdout.readline, ''):
            if line:
                yield f"data: {json.dumps({'log': line.strip()})}\n\n"

        proc.stdout.close()
        proc.wait()

        if proc.returncode != 0 and (proc.returncode < 0 or proc.returncode == 15):
            yield f"data: {json.dumps({'error': '사용자에 의해 실행이 중단되었습니다.'})}\n\n"
        elif proc.returncode != 0:
            yield f"data: {json.dumps({'error': f'실행 오류 (코드 {proc.returncode})'})}\n\n"
        else:
            yield f"data: {json.dumps({'success': True})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"
    finally:
        if process_key in active_processes:
            del active_processes[process_key]
        if cleanup_file and os.path.exists(cleanup_file):
            try: os.remove(cleanup_file)
            except: pass
