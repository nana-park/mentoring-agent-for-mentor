# Direct-file execution support; prefer python -m scripts.<group>.<name>.
if __package__ in (None, ""):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mentoring.config import course_database_id
import asyncio
import os
import json
from google import genai
from google.genai import types
from mentoring.config import load_environment
from mentoring.integrations.notion import NotionAPIClient
from mentoring.services.loaders import DataIngestionLayer

async def generate_one_sentence(client, summary: str) -> str:
    prompt = f"""
    아래는 어떤 학생과의 멘토링 회의록 요약본(Meeting Summary)입니다.
    이 내용을 읽고 전체 회의의 가장 핵심적인 논의 사항을 딱 1~2문장으로 짧게 압축해 주세요.
    (예: "서비스 기획 고도화를 위해 데이터 기반 타겟팅 전략을 수립하고, IA 재설계를 진행하기로 함.")

    [주의사항]
    "네, 알겠습니다", "안녕하세요" 같은 인사말, 불필요한 서론, 마크다운 포맷팅 등은 일절 제외하고 딱 요약 문장만 텍스트로 출력하세요.

    [회의록 요약]
    {summary}
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"제미나이 요약 실패: {e}", flush=True)
        return ""

async def backfill_course(notion_mcp: NotionAPIClient, gemini_client, course_name: str, db_id: str):
    print(f"\n[{course_name}] 멘토링 세션 검사 중...", flush=True)
    try:
        # One Sentence가 비어있는 항목 필터링 (Notion API 필터 제약이 있을 수 있으므로 일단 전부 가져와서 코드 레벨 필터링 병행)
        response = await notion_mcp.query_database(database_id=db_id)
        pages = response.get("results", [])
        
        target_pages = []
        for p in pages:
            props = p.get("properties", {})
            
            # One Sentence 확인
            one_sentence = ""
            if "One Sentence" in props and props["One Sentence"]["rich_text"]:
                one_sentence = "".join([rt.get("plain_text", "") for rt in props["One Sentence"]["rich_text"]])
                
            # 요약이 이미 있고, 이전에 잘못 들어간 응답(인사말이나 긴 줄바꿈)이 아닐 경우에만 스킵
            if one_sentence.strip() and "알겠습니다" not in one_sentence and "붙여넣어" not in one_sentence and "네," not in one_sentence and "안녕하세요" not in one_sentence and "\n" not in one_sentence:
                continue # 이미 올바르게 채워져 있으면 패스
                
            # Meeting Summary 확인
            summary = ""
            if "Meeting Summary" in props and props["Meeting Summary"]["rich_text"]:
                summary = "".join([rt.get("plain_text", "") for rt in props["Meeting Summary"]["rich_text"]])
                
            if not summary.strip():
                continue # 원본 요약이 없으면 요약 불가
                
            target_pages.append((p["id"], summary))
            
        print(f"-> 총 {len(target_pages)}개의 업데이트 필요 항목 발견.", flush=True)
        
        for idx, (page_id, summary) in enumerate(target_pages, 1):
            print(f"  [{idx}/{len(target_pages)}] 요약 중...", flush=True)
            one_line = await generate_one_sentence(gemini_client, summary)
            if one_line:
                # 노션 업데이트
                props_to_update = {
                    "One Sentence": {"rich_text": [{"text": {"content": one_line}}]}
                }
                await notion_mcp.update_page(page_id, props_to_update)
                print(f"  ✅ 업데이트 성공: {one_line}", flush=True)
                
    except Exception as e:
        print(f"강의 처리 중 에러: {e}", flush=True)
        if hasattr(e, 'response'):
            print(f"상세 에러 내용: {e.response.text}", flush=True)

async def main():
    print("===========================================", flush=True)
    print("🚀 One Sentence 백필(Backfill) 스크립트 🚀", flush=True)
    print("===========================================", flush=True)
    
    load_environment()
    notion_token = os.getenv("NOTION_TOKEN")
    if not notion_token:
        print("❌ 에러: .env 파일에 NOTION_TOKEN이 없습니다.")
        return

    notion_mcp = NotionAPIClient(access_token=notion_token)
    ingestion = DataIngestionLayer(notion_mcp)
    gemini_client = genai.Client()
    
    print("1. 활성 강의 목록을 불러옵니다...")
    course_list_db_id = course_database_id()
    courses = await ingestion.load_active_courses(course_list_db_id)
    
    if not courses:
        print("현재 진행 중인 강의가 없습니다.")
        await notion_mcp.close()
        return
        
    for course in courses:
        course_name = course["name"]
        course_page_id = course["page_id"]
        db_ids = await ingestion.scan_course_dbs(course_page_id)
        
        sessions_db_id = db_ids.get("MentoringSessions")
        if sessions_db_id:
            await backfill_course(notion_mcp, gemini_client, course_name, sessions_db_id)
        else:
            print(f"[{course_name}] Mentoring Sessions DB를 찾을 수 없습니다.")
            
    print("\n🎉 모든 백필 작업이 완료되었습니다!")
    await notion_mcp.close()

if __name__ == "__main__":
    asyncio.run(main())
