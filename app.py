import os
import json
import asyncio
import subprocess
import sys
import tempfile
import threading
import datetime
import time
from flask import Flask, render_template, jsonify, request, Response, stream_with_context
from dotenv import load_dotenv
load_dotenv()

from notion_api import NotionAPIClient
from llm_parser import LLMParser

app = Flask(__name__)

# 스크립트 실행을 위한 기본 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

active_processes = {}

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stop/<process_key>', methods=['POST'])
def stop_process(process_key):
    proc = active_processes.get(process_key)
    if proc and proc.poll() is None:
        try:
            if os.name == 'nt':
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                proc.terminate()
        except:
            pass
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "실행 중인 프로세스가 없습니다."})

@app.route('/api/run/auto', methods=['POST'])
def run_auto():
    return Response(stream_with_context(stream_subprocess('auto', [sys.executable, "-u", "run_auto.py"])), mimetype='text/event-stream')

@app.route('/api/run/batch', methods=['POST'])
def run_batch():
    return Response(stream_with_context(stream_subprocess('batch', [sys.executable, "-u", "run_batch.py"])), mimetype='text/event-stream')

@app.route('/api/run/summarize', methods=['POST'])
def run_summarize():
    return Response(stream_with_context(stream_subprocess('summarize', [sys.executable, "-u", "summarize_insights.py"])), mimetype='text/event-stream')

@app.route('/api/history', methods=['GET'])
def get_history():
    try:
        config_path = os.path.join(BASE_DIR, 'db_config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        history_db_id = config.get("IngestionHistory")
        if not history_db_id:
            return jsonify({"success": False, "error": "History DB ID not found"})
            
        client = NotionAPIClient()
        
        async def fetch():
            response = await client.query_database(
                database_id=history_db_id,
                sorts=[{"property": "Processed At", "direction": "descending"}],
                page_size=30
            )
            return response
            
        response = asyncio.run(fetch())
        results = response.get("results", [])
        
        history_data = []
        for row in results:
            props = row.get("properties", {})
            title_prop = props.get("Source Title", {}).get("title", [])
            title = title_prop[0].get("plain_text", "Untitled") if title_prop else "Untitled"
            type_prop = props.get("Type", {}).get("select")
            type_val = type_prop.get("name", "Unknown") if type_prop else "Unknown"
            status_prop = props.get("Status", {}).get("select")
            status_val = status_prop.get("name", "Unknown") if status_prop else "Unknown"
            date_prop = props.get("Processed At", {}).get("date")
            date_val = date_prop.get("start", "") if date_prop else ""
            
            history_data.append({
                "title": title,
                "type": type_val,
                "status": status_val,
                "date": date_val
            })
            
        return jsonify({"success": True, "data": history_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/run/direct', methods=['POST'])
def run_direct():
    data = request.json
    
    # Generate default subject if not provided
    import datetime
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    subject = data.get("subject") or f"[직접 입력] {today_str} 멘토링 세션"
    
    students = data.get("students", [])
    text = data.get("text", "")
    process_key = "direct"
    
    if not students and not text.strip():
        return jsonify({"success": False, "error": "본문 내용이 비어있습니다."})
        
    if process_key in active_processes and active_processes[process_key].poll() is None:
        return jsonify({"success": False, "error": "이미 실행 중입니다."})
        
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        # Save payload either with students array or fallback to raw text
        payload = {"subject": subject}
        if students:
            payload["students"] = students
        else:
            payload["text"] = text
        json.dump(payload, f, ensure_ascii=False)
        temp_path = f.name
        
    return Response(stream_with_context(stream_subprocess('direct', [sys.executable, "-u", "main.py", "--mode", "direct", "--payload", temp_path], cleanup_file=temp_path)), mimetype='text/event-stream')

@app.route('/api/run/direct/analyze', methods=['POST'])
def analyze_direct():
    data = request.json
    text = data.get("text", "")
    
    if not text.strip():
        return jsonify({"success": False, "error": "본문 내용이 비어있습니다."})
        
    try:
        parser = LLMParser()
        # split_text_by_students is an async method
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        students = loop.run_until_complete(parser.split_text_by_students(text))
        loop.close()
        
        return jsonify({"success": True, "students": students})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/docs/<filename>', methods=['GET'])
def get_docs(filename):
    if filename not in ["architecture_diagram.md", "database_schema.md"]:
        return jsonify({"success": False, "error": "허용되지 않은 파일입니다."})
        
    doc_path = os.path.join(BASE_DIR, "docs", filename)
    if not os.path.exists(doc_path):
        return jsonify({"success": False, "error": f"{filename} 파일이 존재하지 않습니다."})
        
    try:
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({"success": True, "content": content})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

CONFIG_FILE = os.path.join(BASE_DIR, "automation_config.json")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"enabled": False, "frequency": "daily", "time": "09:00", "day": "Monday"}

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

@app.route('/api/automation', methods=['GET'])
def get_automation():
    return jsonify({"success": True, "config": load_config()})

@app.route('/api/automation', methods=['POST'])
def set_automation():
    config = request.json
    save_config(config)
    return jsonify({"success": True})

def scheduler_loop():
    while True:
        try:
            config = load_config()
            if config.get("enabled"):
                now = datetime.datetime.now()
                target_time_str = config.get("time", "09:00")
                if target_time_str:
                    target_hour, target_minute = map(int, target_time_str.split(':'))
                    is_time_match = (now.hour == target_hour and now.minute == target_minute)
                    
                    is_day_match = True
                    if config.get("frequency") == "weekly":
                        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                        target_day = config.get("day", "Monday")
                        if days[now.weekday()] != target_day:
                            is_day_match = False
                    
                    if is_time_match and is_day_match:
                        if "batch" not in active_processes or active_processes["batch"].poll() is not None:
                            print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Automation triggered! Running batch mode in background...")
                            proc = subprocess.Popen(
                                [sys.executable, "-u", "main.py", "--mode", "batch"],
                                cwd=BASE_DIR,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL
                            )
                            active_processes["batch"] = proc
        except Exception as e:
            print(f"Scheduler error: {e}")
            
        now = datetime.datetime.now()
        sleep_time = 60 - now.second
        time.sleep(sleep_time)

if __name__ == '__main__':
    # Start scheduler thread
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
        thread = threading.Thread(target=scheduler_loop, daemon=True)
        thread.start()
        
    # Flask 기본 포트인 5000에서 실행
    app.run(debug=True, port=5000)
