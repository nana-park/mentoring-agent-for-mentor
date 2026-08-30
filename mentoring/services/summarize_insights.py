from mentoring.config import course_database_id
import asyncio
import os
import json
from google import genai
from google.genai import types
from mentoring.integrations.notion import NotionAPIClient
from mentoring.services.loaders import DataIngestionLayer
from mentoring.services.upsert import parse_markdown_to_rich_text

async def fetch_insights(notion_mcp: NotionAPIClient, db_id: str, insight_type: str = "기획 실무"):
    print(f"[{insight_type}] 인사이트를 수집 중입니다...")
    try:
        response = await notion_mcp.query_database(
            database_id=db_id,
            filter_payload={
                "property": "Insight Type",
                "select": {"equals": insight_type}
            }
        )

        insights = []
        for page in response.get("results", []):
            props = page.get("properties", {})

            title = ""
            if "Insight Title" in props and props["Insight Title"]["title"]:
                title = props["Insight Title"]["title"][0]["plain_text"]

            summary = ""
            if "Summary" in props and props["Summary"]["rich_text"]:
                summary = props["Summary"]["rich_text"][0]["plain_text"]

            if title or summary:
                insights.append(f"- 제목: {title}\n  내용: {summary}")

        return insights
    except Exception as e:
        print(f"인사이트 수집 실패: {e}")
        return []

async def generate_retrospective(insights: list) -> str:
    print("🧠 제미나이가 리포트를 작성 중입니다...")
    client = genai.Client()

    insights_text = "\n\n".join(insights)

    prompt = f"""
    당신은 서비스 기획 실무 역량을 키우고자 하는 강사 본인입니다.
    이번 강의를 진행하면서 학생들을 멘토링하며 얻은 '기획 실무' 관련 인사이트 모음이 아래에 주어집니다.

    이 데이터를 바탕으로, 강사 본인의 향후 실무 기획 업무나 다음 강의 준비에 실질적으로 도움이 될 수 있는 멋진 회고록(리포트)을 작성해 주세요.

    [인사이트 모음]
    {insights_text}

    [요구사항]
    1. 제목은 넣지 마세요 (노션 API에서 따로 제목 블록을 추가할 것입니다).
    2. 마크다운 형식으로 가독성 좋게 작성해 주세요.
    3. 핵심 배울 점, 수강생들이 자주 겪는 어려움과 인사이트, 향후 실무/강의 적용점 등의 구조로 나누어 작성해 주세요.
    4. 너무 길지 않고, 임팩트 있게 요약해 주세요.
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        print(f"제미나이 호출 실패: {e}")
        return ""

async def append_to_notion_page(notion_mcp: NotionAPIClient, page_id: str, markdown_text: str):
    print("✍️ 노션 페이지에 리포트를 기록합니다...")

    parsed_blocks = []
    lines = markdown_text.split('\n')

    current_paragraph = ""
    def flush_p():
        nonlocal current_paragraph
        if current_paragraph.strip():
            parsed_blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": parse_markdown_to_rich_text(current_paragraph.strip())}
            })
            current_paragraph = ""

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_p()
            continue

        if stripped.startswith('### '):
            flush_p()
            parsed_blocks.append({
                "object": "block", "type": "heading_3",
                "heading_3": {"rich_text": parse_markdown_to_rich_text(stripped[4:])}
            })
        elif stripped.startswith('## '):
            flush_p()
            parsed_blocks.append({
                "object": "block", "type": "heading_2",
                "heading_2": {"rich_text": parse_markdown_to_rich_text(stripped[3:])}
            })
        elif stripped.startswith('# '):
            flush_p()
            parsed_blocks.append({
                "object": "block", "type": "heading_1",
                "heading_1": {"rich_text": parse_markdown_to_rich_text(stripped[2:])}
            })
        elif stripped.startswith('* ') or stripped.startswith('- '):
            flush_p()
            parsed_blocks.append({
                "object": "block", "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": parse_markdown_to_rich_text(stripped[2:])}
            })
        elif stripped.startswith('> '):
            flush_p()
            parsed_blocks.append({
                "object": "block", "type": "quote",
                "quote": {"rich_text": parse_markdown_to_rich_text(stripped[2:])}
            })
        else:
            if current_paragraph:
                current_paragraph += "\n" + line
            else:
                current_paragraph = line
    flush_p()

    if not parsed_blocks:
        parsed_blocks.append({"object": "block", "type": "paragraph", "paragraph": {"rich_text": [{"text": {"content": "내용 없음"}}]}})

    blocks = [
        {
            "object": "block",
            "type": "toggle",
            "toggle": {
                "rich_text": [{"text": {"content": "🔥 기획 실무 회고록"}}],
                "children": parsed_blocks
            }
        }
    ]

    try:
        await notion_mcp.append_block_children(page_id, blocks)
        print("✅ 노션 강의 페이지 본문에 토글 형태로 기록 완료!")
    except Exception as e:
        print(f"노션 기록 실패: {e}")

async def main():
    print("===========================================")
    print("🔥 멘토링 실무 인사이트 요약 스크립트 🔥")
    print("===========================================")

    from mentoring.config import load_environment
    load_environment()

    notion_token = os.getenv("NOTION_TOKEN")
    if not notion_token:
        print("❌ 에러: .env 파일에 NOTION_TOKEN이 없습니다.")
        return

    notion_mcp = NotionAPIClient(access_token=notion_token)
    ingestion = DataIngestionLayer(notion_mcp)

    print("1. 활성 강의 목록을 불러옵니다...")
    course_list_db_id = course_database_id() # main.py에 있는 global_course_db_id와 동일
    courses = await ingestion.load_active_courses(course_list_db_id)

    if not courses:
        print("현재 진행 중인 강의가 없습니다.")
        await notion_mcp.close()
        return

    print("\n[현재 등록된 강의 목록]")
    for i, c in enumerate(courses):
        print(f"{i+1}. {c['name']}")

    import sys
    if sys.stdin and sys.stdin.isatty():
        choice = input("\n요약할 강의 번호를 선택하세요 (종료하려면 q): ")
        if choice.lower() == 'q':
            await notion_mcp.close()
            return

        try:
            idx = int(choice) - 1
            selected_course = courses[idx]
        except (ValueError, IndexError):
            print("잘못된 입력입니다.")
            await notion_mcp.close()
            return
    else:
        print("\n[UI 모드] 자동으로 첫 번째 강의를 선택하여 요약합니다.")
        selected_course = courses[0]

    course_name = selected_course["name"]
    course_page_id = selected_course["page_id"]
    db_ids = await ingestion.scan_course_dbs(course_page_id)
    mentor_insights_db = db_ids.get("MentorInsights")

    if not mentor_insights_db:
        print(f"❌ '{course_name}' 하위에 MentorInsights DB가 없습니다.")
        await notion_mcp.close()
        return

    insights = await fetch_insights(notion_mcp, mentor_insights_db, "기획 실무")
    if not insights:
        print("이 강의에는 '기획 실무'로 분류된 인사이트가 없습니다.")
        await notion_mcp.close()
        return

    print(f"\n총 {len(insights)}개의 기획 실무 인사이트를 찾았습니다.")

    report = await generate_retrospective(insights)
    if not report:
        await notion_mcp.close()
        return

    print("\n[리포트 미리보기]")
    print("-" * 50)
    print(report)
    print("-" * 50)

    await append_to_notion_page(notion_mcp, course_page_id, report)

    await notion_mcp.close()

if __name__ == "__main__":
    asyncio.run(main())
