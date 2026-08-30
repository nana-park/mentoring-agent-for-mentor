"""Flask routes. Process execution and scheduling live in sibling modules."""
import asyncio
import json
import os
import subprocess
import tempfile
import threading
from flask import Flask, render_template, jsonify, request, Response, stream_with_context
from mentoring.config import DB_CONFIG_FILE, DOCS_DIR, WEB_DIR, load_environment
from mentoring.integrations.notion import NotionAPIClient
from mentoring.services.llm_parser import LLMParser
from mentoring.web.processes import active_processes, stream_subprocess, pipeline_command, summarize_command
from mentoring.web.scheduler import load_config, save_config, scheduler_loop

from mentoring.web.context_routes import context_routes

load_environment()
app = Flask(__name__, template_folder=str(WEB_DIR / "templates"),
            static_folder=str(WEB_DIR / "static"), static_url_path="/static")
app.register_blueprint(context_routes)

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
    return Response(stream_with_context(stream_subprocess('auto', pipeline_command("auto"))), mimetype='text/event-stream')

@app.route('/api/run/batch', methods=['POST'])
def run_batch():
    return Response(stream_with_context(stream_subprocess('batch', pipeline_command("batch"))), mimetype='text/event-stream')

@app.route('/api/run/summarize', methods=['POST'])
def run_summarize():
    return Response(stream_with_context(stream_subprocess('summarize', summarize_command())), mimetype='text/event-stream')

@app.route('/api/history', methods=['GET'])
def get_history():
    try:
        config_path = DB_CONFIG_FILE
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        history_db_id = config.get("IngestionHistory")
        if not history_db_id:
            return jsonify({"success": False, "error": "History DB ID not found"})

        client = NotionAPIClient(access_token=os.getenv("NOTION_TOKEN"))

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

    return Response(stream_with_context(stream_subprocess('direct', pipeline_command("direct", temp_path), cleanup_file=temp_path)), mimetype='text/event-stream')

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
    if filename not in ["architecture_diagram.md", "database_schema.md", "project_structure.md", "mentor_insights.md"]:
        return jsonify({"success": False, "error": "허용되지 않은 파일입니다."})

    doc_path = DOCS_DIR / filename
    if not os.path.exists(doc_path):
        return jsonify({"success": False, "error": f"{filename} 파일이 존재하지 않습니다."})

    try:
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return jsonify({"success": True, "content": content})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/automation', methods=['GET'])
def get_automation():
    return jsonify({"success": True, "config": load_config()})

@app.route('/api/automation', methods=['POST'])
def set_automation():
    config = request.json
    save_config(config)
    return jsonify({"success": True})

def main():
    # One process and one scheduler; no duplicate background thread from a reloader.
    threading.Thread(target=scheduler_loop, daemon=True).start()
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
