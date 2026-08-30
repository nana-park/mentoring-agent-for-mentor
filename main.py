import asyncio
import json
import os
import argparse
from mcp_client import NotionMCPClient
from notion_api import NotionAPIClient
from loaders import DataIngestionLayer
from llm_parser import LLMParser
from upsert import NotionUpsertHandler
from ingestion_tracker import IngestionTracker
from google_api_client import GoogleWorkspaceClient
from batch_processor import BatchProcessor

async def process_source(source_text: str, source_id: str, subject: str, source_type: str, 
                         ingestion: DataIngestionLayer, parser: LLMParser, upsert: NotionUpsertHandler, 
                         course_map: dict, notion_mcp, global_review_queue_id: str):
    
    print(f"\n[{source_type}] '{subject}' 처리 시작...")
    
    # 1. Flatten lists for LLM
    active_courses_list = list(course_map.keys())
    students_list = []
    for cname, cdata in course_map.items():
        for st in cdata["students"]:
            alias = st.get("alias", "")
            bg = st.get("background", "")
            st_info = f"{st['name']} ({cname})"
            if alias: st_info += f" - 별명/오타: {alias}"
            if bg: st_info += f" - 관련 주제/배경: {bg[:50]}"
            students_list.append(st_info)
            
    # 2. 전역 중복 확인 (제미나이 API 호출 비용 절약)
    is_already_processed = False
    for cname, cdata in course_map.items():
        history_db = cdata["db_ids"].get("IngestionHistory")
        if history_db:
            temp_tracker = IngestionTracker(notion_mcp, history_db)
            if await temp_tracker.is_processed(source_id):
                is_already_processed = True
                break
                
    if is_already_processed:
        print(f"⏩ 이미 처리된 항목입니다. (스킵)")
        return
        
    # 3. 제미나이 매칭
    print("🔍 제미나이에게 학생/강의 매칭을 요청합니다...")
    match = await parser.identify_context(source_text, subject, active_courses_list, students_list)
    student_name = match.get("student_name", "")
    course_name = match.get("course_name", "")
    multiple_students_detected = match.get("multiple_students_detected", False)
    
    # 임시 트래커 객체 (전체 학생 검색을 위해)
    tracker = IngestionTracker(notion_mcp, None)

    if multiple_students_detected and source_type != "Direct Entry":
        print("⚠️ 섞인 회의록(다수 학생)이 감지되었습니다! (글로벌 큐로 전송)")
        await upsert.insert_global_review_queue(
            global_review_queue_id, 
            error_title=f"[분리 요망] {subject}", 
            error_reason="여러 학생(2명 이상)의 멘토링 내용이 하나의 회의록에 섞여 있습니다. 수동으로 텍스트를 분리해서 넣어주세요.", 
            raw_text=source_text
        )
        await tracker.record_ingestion(source_id, subject, "Multiple", source_type, "Review Required")
        return

    if not student_name or not course_name or course_name not in course_map:
        print("❌ 학생 또는 강의를 찾지 못했습니다. 매칭 실패 (글로벌 큐로 전송).")
        await upsert.insert_global_review_queue(
            global_review_queue_id, 
            error_title=f"[매칭 실패] {subject}", 
            error_reason=f"학생 또는 강의를 찾을 수 없습니다. (추출된 학생: {student_name}, 강의: {course_name})", 
            raw_text=source_text
        )
        
        # We must record it as Failed in the tracker so it doesn't loop infinitely!
        # Since we don't have course_name, we cannot get the Ingestion History DB ID easily from course_map.
        # But wait, Ingestion History is a course DB!
        # We can't record it if we don't know the course...
        # So we just return. The batch processor archives the file, but Gmail will keep fetching it?
        # Actually, GoogleWorkspaceClient only fetches UNREAD emails and marks them as READ after fetching!
        # So it won't loop infinitely for Gmail. For batch, it archives.
        return
        
    print(f"✅ 매칭 성공: {student_name} ({course_name})")
    
    cdata = course_map[course_name]
    db_ids = cdata["db_ids"]
    student_page_id = next((s["page_id"] for s in cdata["students"] if s["name"] == student_name), None)
    
    tracker = IngestionTracker(notion_mcp, db_ids.get("IngestionHistory"))
    
    try:
        # 4. 히스토리 로드
        history = await ingestion.load_historical_context(student_name, db_ids)
        
        # 5. 파싱
        print("🧠 제미나이가 멘토링 세션을 파싱합니다...")
        student_obj = next((s for s in cdata["students"] if s["name"] == student_name), None)
        existing_background = student_obj["background"] if student_obj else ""
        
        parsed_data = await parser.parse_mentoring_data(source_text, subject, student_name, course_name, history, existing_background)
        
        # 6. 업서트 (student_page_id 추가)
        print("✍️ 노션에 데이터를 기록합니다...")
        await upsert.upsert_session(parsed_data, student_name, course_name, db_ids, student_page_id, source_text)
        
        # 7. 트래커 기록
        await tracker.record_ingestion(source_id, subject, student_name, source_type, "Success")
        print(f"🎉 '{subject}' 처리 완료!")
        
    except Exception as e:
        print(f"❌ 데이터 처리 실패: {e}")
        await tracker.record_ingestion(source_id, subject, student_name, source_type, "Failed")

async def run_pipeline(mode="auto"):
    from dotenv import load_dotenv
    load_dotenv()
    
    notion_token = os.getenv("NOTION_TOKEN")
    if not notion_token:
        print("❌ 에러: .env 파일에 NOTION_TOKEN이 없습니다.")
        sys.exit(1)

    notion_mcp = NotionAPIClient(access_token=notion_token)
    ingestion = DataIngestionLayer(notion_mcp)
    parser = LLMParser()
    upsert = NotionUpsertHandler(notion_mcp)

    print("📚 최상위 '강의 일정' DB에서 진행 중인 강의를 찾습니다...")
    # NOTE: The Course Schedule DB ID must have hyphens for newer Notion API versions
    global_course_db_id = "358c919e-34d1-80f0-9573-edb4e42a261a" 
    active_courses = await ingestion.load_active_courses(global_course_db_id)
    
    if not active_courses:
        print("❌ 현재 진행 중인 (또는 최근) 강의를 찾을 수 없습니다. 노션 설정을 확인하세요.")
        sys.exit(1)
        
    course_map = {}
    all_keywords = set()
    
    print(f"   👉 찾은 활성 강의: {len(active_courses)}개")
    for course in active_courses:
        cname = course["name"]
        print(f"   🔍 '{cname}' 내부의 CRM DB들을 스캔합니다...")
        db_ids = await ingestion.scan_course_dbs(course["page_id"])
        
        if "Students" in db_ids:
            students = await ingestion.load_students(db_ids["Students"])
        else:
            students = []
            print(f"      ⚠️ '{cname}' 내부에 학생 DB가 없습니다.")
            
        print(f"   🏗️ '{cname}' 과제 및 멘토링 빈칸 자동 세팅(Pre-populate)을 수행합니다...")
        await upsert.sync_course_placeholders(course, db_ids, students)
            
        course_map[cname] = {
            "page_id": course["page_id"],
            "keyword": course["keyword"],
            "db_ids": db_ids,
            "students": students
        }
        all_keywords.add(course["keyword"])
        print(f"      - 매핑된 DB: {len(db_ids)}개, 등록된 학생: {len(students)}명")
    
    if mode == "auto":
        print("📧 구글 메일(Google Docs) 자동 수집을 시작합니다...")
        try:
            google_client = GoogleWorkspaceClient()
            notes = google_client.fetch_unread_meeting_notes(keywords=list(all_keywords))
            if not notes:
                print("수집할 새 메일이 없습니다.")
            for note in notes:
                await process_source(
                    source_text=note["text"],
                    source_id=note["msg_id"],
                    subject=note["subject"],
                    source_type="Email",
                    ingestion=ingestion, parser=parser, upsert=upsert,
                    course_map=course_map, notion_mcp=notion_mcp,
                    global_review_queue_id="374c919e-34d1-8040-ab19-d3ac7d73e526"
                )
        except Exception as e:
            print(f"구글 연동 에러: {e}")
            
    elif mode == "batch":
        print("📁 수동 로컬 폴더(Batch) 처리를 시작합니다...")
        base_dir = os.path.dirname(os.path.abspath(__file__))
        inbox_dir = os.path.join(base_dir, "inbox")
        archive_dir = os.path.join(base_dir, "archive")
        bp = BatchProcessor(inbox_dir, archive_dir)
        files = bp.fetch_unprocessed_files()
        
        if not files:
            print(f"'{inbox_dir}' 폴더에 처리할 텍스트 파일이 없습니다.")
            
        for f in files:
            await process_source(
                source_text=f["text"],
                source_id=f["msg_id"],
                subject=f["subject"],
                source_type="Local File",
                ingestion=ingestion, parser=parser, upsert=upsert,
                course_map=course_map, notion_mcp=notion_mcp,
                global_review_queue_id="374c919e-34d1-8040-ab19-d3ac7d73e526"
            )
            bp.archive_file(f["filepath"])
            
    elif mode == "direct":
        print("⚡ 웹 관제탑 실시간 직접 입력(Direct Entry) 처리를 시작합니다...")
        parser_args = argparse.ArgumentParser()
        parser_args.add_argument("--mode")
        parser_args.add_argument("--payload")
        
        # We need to re-parse the args to get payload
        args = parser_args.parse_known_args()[0]
        
        if not args.payload or not os.path.exists(args.payload):
            print("❌ 에러: 유효한 payload JSON 파일이 제공되지 않았습니다.")
            import sys
            sys.exit(1)
            
        with open(args.payload, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        subject = data.get("subject", "직접 입력 세션")
        students = data.get("students", [])
        
        if not students:
            # Fallback for old payloads or single text
            text = data.get("text", "")
            students = [{"name": "Unknown", "content": text}]
            
        import hashlib
        
        for i, stu in enumerate(students):
            stu_name = stu.get("name", "Unknown")
            stu_text = stu.get("content", "")
            if not stu_text.strip():
                continue
                
            msg_id = hashlib.md5(f"{subject}_{stu_name}_{stu_text[:50]}".encode('utf-8')).hexdigest()
            print(f"\n--- [{i+1}/{len(students)}] {stu_name} 학생 처리 중 ---")
            
            await process_source(
                source_text=stu_text,
                source_id=msg_id,
                subject=f"{subject} - {stu_name}",
                source_type="Direct Entry",
                ingestion=ingestion, parser=parser, upsert=upsert,
                course_map=course_map, notion_mcp=notion_mcp,
                global_review_queue_id="374c919e-34d1-8040-ab19-d3ac7d73e526"
            )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mentoring CRM Pipeline")
    parser.add_argument("--mode", choices=["auto", "batch", "direct"], default="auto", help="실행 모드 (auto: 구글메일, batch: 로컬폴더, direct: 웹 직접입력)")
    parser.add_argument("--payload", help="JSON payload file path for direct mode", default=None)
    args = parser.parse_args()
    asyncio.run(run_pipeline(args.mode))
