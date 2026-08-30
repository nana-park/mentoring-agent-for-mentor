import os
import requests
from dotenv import load_dotenv

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def create_database(parent_page_id: str, title: str, properties: dict):
    url = "https://api.notion.com/v1/databases"
    payload = {
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "title": [{"type": "text", "text": {"content": title}}],
        "properties": properties
    }
    response = requests.post(url, json=payload, headers=HEADERS)
    if response.status_code == 200:
        print(f"??DB Created: {title}")
        return response.json()["id"]
    else:
        print(f"??Failed to create {title}: {response.text}")
        return None

def setup_dbs(parent_page_id: str):
    print("?? ?몄뀡 留덉뒪??CRM ?곗씠?곕쿋?댁뒪 7媛??먮룞 ?앹꽦???쒖옉?⑸땲??..\n")

    # 1. Courses DB
    course_props = {
        "Course Name": {"title": {}},
        "Status": {"select": {"options": [{"name": "Active", "color": "green"}, {"name": "Closed", "color": "gray"}]}},
        "Expected Sessions": {"number": {}}
    }
    course_id = create_database(parent_page_id, "?뱴 Courses (媛뺤쓽 留덉뒪??", course_props)

    # 2. Students DB
    student_props = {
        "Student Name": {"title": {}},
        "Status": {"select": {"options": [{"name": "?윟 ?뺤긽 吏꾪뻾", "color": "green"}, {"name": "?윞 怨쇱젣 吏??, "color": "yellow"}, {"name": "?뵶 ?댄깉 ?꾪뿕", "color": "red"}, {"name": "狩??곗닔 ?섍컯??, "color": "blue"}]}},
        "Background": {"rich_text": {}}
    }
    student_id = create_database(parent_page_id, "?쭛?랅윃?Students (?숈깮 CRM)", student_props)

    # 3. Mentoring Sessions DB
    session_props = {
        "UniqueKey": {"title": {}},
        "Session Date": {"date": {}},
        "Meeting Summary": {"rich_text": {}}
    }
    session_id = create_database(parent_page_id, "?뮠 Mentoring Sessions", session_props)

    # 4. Assignments DB
    assignment_props = {
        "UniqueKey": {"title": {}},
        "Assignment Title": {"rich_text": {}},
        "Status": {"select": {"options": [{"name": "Not Started", "color": "gray"}, {"name": "In Progress", "color": "blue"}, {"name": "Submitted", "color": "green"}, {"name": "Revised", "color": "purple"}]}},
        "Due Date": {"date": {}}
    }
    assign_id = create_database(parent_page_id, "?뱷 Assignments", assignment_props)

    # 5. Showcase Projects
    showcase_props = {
        "Project Name": {"title": {}},
        "Result Link": {"url": {}}
    }
    create_database(parent_page_id, "?룇 Showcase Projects", showcase_props)

    # 6. Mentor Insights
    insights_props = {
        "Insight Title": {"title": {}},
        "Insight Type": {"select": {"options": [{"name": "?숈깮 ?대젮?", "color": "red"}, {"name": "援먯쑁 媛쒖꽑", "color": "blue"}]}},
        "Summary": {"rich_text": {}}
    }
    create_database(parent_page_id, "?쭬 Mentor Insights", insights_props)

    # 7. Review Queue
    review_props = {
        "Review Title": {"title": {}},
        "Confidence": {"number": {}},
        "Needs Human Review": {"checkbox": {}}
    }
    create_database(parent_page_id, "?슚 Review Queue", review_props)
    
    print("\n?럦 紐⑤뱺 DB ?앹꽦???꾨즺?섏뿀?듬땲??")
    print("?뮕 ?? ?몄뀡 ?붾㈃?먯꽌 DB 媛꾩쓽 Relation(愿怨꾪삎) ?띿꽦留?留덉슦?ㅻ줈 吏곸젒 ?곌껐?댁＜?몄슂.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        TARGET_PAGE_ID = sys.argv[1]
        setup_dbs(TARGET_PAGE_ID)
    else:
        print("Usage: python setup_notion_dbs.py <page_id>")
