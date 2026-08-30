from mentoring.integrations.notion import NotionAPIClient

class DataIngestionLayer:
    def __init__(self, mcp_client: NotionAPIClient):
        self.mcp = mcp_client
        
    async def load_historical_context(self, student_page_id: str, db_ids: dict):
        if 'MentoringSessions' not in db_ids or not student_page_id: return []
        
        try:
            response = await self.mcp.query_database(
                db_ids['MentoringSessions'],
                filter_payload={
                    "property": "🧑‍🎓 Students (학생 CRM)",
                    "relation": {
                        "contains": student_page_id
                    }
                },
            sorts=[
                {
                    "property": "Session Date",
                    "direction": "descending"
                }
            ],
            page_size=3
            )
            
            history = []
            for page in response.get("results", []):
                try:
                    date = page["properties"]["Session Date"]["date"]["start"]
                    summary = page["properties"]["Meeting Summary"]["rich_text"][0]["plain_text"]
                    history.append(f"Date: {date}, Summary: {summary}")
                except (KeyError, IndexError):
                    continue
                    
            return history
        except Exception as e:
            print(f"Error loading historical context: {e}")
            return []
        
    async def load_notion_memo(self, page_id: str):
        if page_id == "fake_memo_block_id":
            return "This is a mock memo text."
            
        try:
            response = await self.mcp.get_block_children(page_id)
            blocks = response.get("results", [])
            
            memo_text = ""
            for block in blocks:
                if block["type"] == "paragraph":
                    rich_text = block["paragraph"].get("rich_text", [])
                    if rich_text:
                        memo_text += rich_text[0].get("plain_text", "") + "\n"
                        
            return memo_text
        except Exception as e:
            return f"Failed to load memo: {e}"

    async def load_active_courses(self, db_id: str):
        """
        Load active courses where today's date is between 시작일 and 종료일.
        If no active courses are found, fallback to the most recent course.
        """
        from datetime import datetime
        now_iso = datetime.now().strftime("%Y-%m-%d")
        
        def parse_courses_from_response(response_obj):
            parsed = []
            for page in response_obj.get("results", []):
                try:
                    props = page["properties"]
                    title_prop = next(p for p in props.values() if p["type"] == "title")
                    
                    if title_prop["title"]:
                        course_name = title_prop["title"][0]["plain_text"]
                        
                        # Fetch custom keyword if exists, else default to '회의록'
                        keyword = "회의록"
                        if "메일 자동화 검색 키워드" in props and props["메일 자동화 검색 키워드"]["type"] == "rich_text" and props["메일 자동화 검색 키워드"]["rich_text"]:
                            keyword = props["메일 자동화 검색 키워드"]["rich_text"][0]["plain_text"]
                        elif "키워드" in props and props["키워드"]["type"] == "rich_text" and props["키워드"]["rich_text"]:
                            keyword = props["키워드"]["rich_text"][0]["plain_text"]
                        elif "검색 키워드" in props and props["검색 키워드"]["type"] == "rich_text" and props["검색 키워드"]["rich_text"]:
                            keyword = props["검색 키워드"]["rich_text"][0]["plain_text"]
                            
                        has_assignments = props.get("과제 여부", {}).get("checkbox", False)
                        num_assignments = props.get("과제 수", {}).get("number", 0) or 0
                        has_mentoring = props.get("1:1 멘토링 여부", {}).get("checkbox", False)
                        num_mentoring = props.get("1:1 멘토링 수", {}).get("number", 0) or 0
                            
                        parsed.append({
                            "name": course_name,
                            "page_id": page["id"],
                            "keyword": keyword,
                            "has_assignments": has_assignments,
                            "num_assignments": num_assignments,
                            "has_mentoring": has_mentoring,
                            "num_mentoring": num_mentoring
                        })
                except Exception:
                    continue
            return parsed

        try:
            response = await self.mcp.query_database(
                db_id,
                filter_payload={
                    "and": [
                        {
                            "property": "시작일",
                            "date": {
                                "on_or_before": now_iso
                            }
                        },
                        {
                            "property": "종료일",
                            "date": {
                                "on_or_after": now_iso
                            }
                        }
                    ]
                }
            )
            
            courses = parse_courses_from_response(response)
            
            if not courses:
                print("현재 진행 중인 강의가 없어, 가장 최근 강의 1개를 가져옵니다.")
                fallback_response = await self.mcp.query_database(
                    db_id,
                    sorts=[
                        {
                            "property": "종료일",
                            "direction": "descending"
                        }
                    ],
                    page_size=1
                )
                courses = parse_courses_from_response(fallback_response)
                
            return courses
        except Exception as e:
            print(f"Error loading active courses: {e}")
            return []

    async def scan_course_dbs(self, course_page_id: str):
        """
        Dynamically scan a course page to find its child databases.
        Returns a dictionary of mapped db_ids.
        """
        db_ids = {}
        try:
            response = await self.mcp.get_block_children(course_page_id)
            for block in response.get("results", []):
                if block["type"] == "child_database":
                    title = block["child_database"]["title"]
                    if "Students" in title or "학생" in title:
                        db_ids["Students"] = block["id"]
                    elif "Mentoring Sessions" in title or "멘토링" in title:
                        db_ids["MentoringSessions"] = block["id"]
                    elif "Assignments" in title or "과제" in title:
                        db_ids["Assignments"] = block["id"]
                    elif "Showcase Projects" in title or "쇼케이스" in title:
                        db_ids["ShowcaseProjects"] = block["id"]
                    elif "Mentor Insights" in title or "인사이트" in title:
                        db_ids["MentorInsights"] = block["id"]
                    elif "Review Queue" in title or "리뷰" in title:
                        db_ids["ReviewQueue"] = block["id"]
                    elif "Ingestion History" in title or "히스토리" in title:
                        db_ids["IngestionHistory"] = block["id"]
                        
            return db_ids
        except Exception as e:
            print(f"Error scanning course DBs: {e}")
            return {}

    async def load_students(self, db_id: str):
        """
        Load all students to provide context to the LLM.
        """
        try:
            response = await self.mcp.query_database(db_id)
            students = []
            for page in response.get("results", []):
                try:
                    props = page["properties"]
                    title_prop = next(p for p in props.values() if p["type"] == "title")
                    if title_prop["title"]:
                        alias_prop = props.get("Alias", {})
                        alias_val = alias_prop.get("rich_text", [{"plain_text": ""}])[0].get("plain_text", "") if alias_prop.get("rich_text") else ""
                        
                        bg_prop = props.get("Background", {})
                        bg_val = bg_prop.get("rich_text", [{"plain_text": ""}])[0].get("plain_text", "") if bg_prop.get("rich_text") else ""
                        
                        students.append({
                            "name": title_prop["title"][0]["plain_text"],
                            "alias": alias_val,
                            "background": bg_val,
                            "page_id": page["id"]
                        })
                except Exception:
                    continue
            return students
        except Exception as e:
            print(f"Error loading students: {e}")
            return []
