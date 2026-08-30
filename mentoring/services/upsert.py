import json
import re
from mentoring.integrations.notion import NotionAPIClient
from mentoring.models import ParsedMentoringSession
from mentoring.services.mentor_insights import insight_summary, plain_rich_text

def parse_markdown_to_rich_text(text: str):
    """
    Convert a string with **bold** markdown into Notion API rich_text blocks.
    """
    if not text:
        return []
    parts = re.split(r'(\*\*.*?\*\*)', text)
    rich_text_list = []
    for part in parts:
        if not part: continue
        if part.startswith('**') and part.endswith('**'):
            rich_text_list.append({
                "text": {"content": part[2:-2]},
                "annotations": {"bold": True}
            })
        else:
            rich_text_list.append({
                "text": {"content": part}
            })
    return rich_text_list

class NotionUpsertHandler:
    def __init__(self, mcp_client: NotionAPIClient):
        self.mcp = mcp_client

    async def sync_course_placeholders(self, course: dict, db_ids: dict, students_list: list):
        print(f"Syncing placeholders for course: {course['name']}")
        assign_db = db_ids.get("Assignments")
        mentor_db = db_ids.get("MentoringSessions")
        
        for student in students_list:
            student_id = student["page_id"]
            student_name = student["name"]
            
            # Sync Assignments
            if course.get("has_assignments") and assign_db:
                num_assignments = course.get("num_assignments", 0)
                for i in range(1, num_assignments + 1):
                    title = f"{i}차과제"
                    filter_payload = {
                        "and": [
                            {"property": "Assignment Title", "title": {"equals": title}},
                            {"property": "🧑‍🎓 Students (학생 CRM)", "relation": {"contains": student_id}}
                        ]
                    }
                    existing = await self.find_existing_record(assign_db, filter_payload)
                    if not existing:
                        print(f"Creating placeholder: {student_name} - {title}")
                        try:
                            await self.mcp.create_page(assign_db, {
                                "Assignment Title": {"title": [{"text": {"content": title}}]},
                                "🧑‍🎓 Students (학생 CRM)": {"relation": [{"id": student_id}]}
                            })
                        except Exception as e:
                            print(f"Failed to create assignment placeholder: {e}")
            
            # Sync Mentoring Sessions
            if course.get("has_mentoring") and mentor_db:
                num_mentoring = course.get("num_mentoring", 0)
                for i in range(1, num_mentoring + 1):
                    title = f"{i}차 멘토링"
                    filter_payload = {
                        "and": [
                            {"property": "Session Title", "title": {"equals": title}},
                            {"property": "🧑‍🎓 Students (학생 CRM)", "relation": {"contains": student_id}}
                        ]
                    }
                    existing = await self.find_existing_record(mentor_db, filter_payload)
                    if not existing:
                        print(f"Creating placeholder: {student_name} - {title}")
                        try:
                            await self.mcp.create_page(mentor_db, {
                                "Session Title": {"title": [{"text": {"content": title}}]},
                                "🧑‍🎓 Students (학생 CRM)": {"relation": [{"id": student_id}]}
                            })
                        except Exception as e:
                            print(f"Failed to create mentoring placeholder: {e}")
        
    async def find_existing_record(self, db_id: str, filter_payload: dict):
        try:
            response = await self.mcp.query_database(
                db_id,
                filter_payload=filter_payload
            )
            results = response.get("results", [])
            return results[0] if results else None
        except Exception as e:
            print(f"Error finding record: {e}")
            return None
        
    async def upsert_session(self, session_data: ParsedMentoringSession, student_name: str, course_name: str, db_ids: dict, student_page_id: str, raw_note: str = ""):
        # 1. Routing & Confidence Check
        if session_data.routing.confidence < 0.7:
            print("Confidence too low. Sending to Review Queue.")
            await self._insert_to_review_queue(db_ids.get('ReviewQueue'), session_data)
            return

        session_page_id = None
        if 'MentoringSessions' in db_ids and student_page_id:
            session_date = session_data.sessionDate
            
            # Find an empty placeholder (where Session Date is empty)
            empty_filter = {
                "and": [
                    {"property": "Session Date", "date": {"is_empty": True}},
                    {"property": "🧑‍🎓 Students (학생 CRM)", "relation": {"contains": student_page_id}}
                ]
            }
            empty_placeholder = await self.find_existing_record(db_ids['MentoringSessions'], empty_filter)
            
            if empty_placeholder:
                print(f"Using empty placeholder for {session_date}...")
                session_page_id = empty_placeholder['id']
                await self._update_session(session_page_id, session_data, student_page_id, raw_note)
            else:
                print(f"No placeholder found. Creating new session row...")
                new_page = await self._create_session(db_ids['MentoringSessions'], "새 멘토링 세션", session_data, student_page_id, raw_note)
                session_page_id = new_page.get("id") if new_page else None
            
        # 3. Insert Mentor Insights
        if session_data.mentorInsights and 'MentorInsights' in db_ids and session_page_id:
            await self._insert_insights(db_ids['MentorInsights'], session_data.mentorInsights, student_page_id, session_page_id)
            
        # 4. Update Student CRM Profile
        if student_page_id:
            await self._update_student_profile(student_page_id, session_data.mentorBrief)
            
        # 5. Sync Assignment Subject if extracted
        if session_data.mentorBrief and session_data.mentorBrief.assignmentSubject and 'Assignments' in db_ids:
            await self._sync_assignment_subject(db_ids['Assignments'], student_page_id, session_data.mentorBrief.assignmentSubject)
            
        # 6. Reorder and Rename Sessions Chronologically
        await self._reorder_sessions(db_ids['MentoringSessions'], student_page_id)

    async def _sync_assignment_subject(self, assign_db_id: str, student_page_id: str, subject: str):
        if not assign_db_id or not student_page_id or not subject: return
        
        try:
            response = await self.mcp.query_database(
                assign_db_id,
                filter_payload={
                    "property": "🧑‍🎓 Students (학생 CRM)",
                    "relation": {"contains": student_page_id}
                }
            )
            for page in response.get("results", []):
                # Update all assignments for this student to keep the subject synced
                try:
                    current_subject = ""
                    if "Subject" in page["properties"] and page["properties"]["Subject"]["rich_text"]:
                        current_subject = page["properties"]["Subject"]["rich_text"][0]["plain_text"]
                        
                    if current_subject != subject:
                        print(f"🔄 Syncing Assignment Subject: '{current_subject}' -> '{subject}'")
                        await self.mcp.update_page(page["id"], {
                            "Subject": {"rich_text": [{"text": {"content": subject}}]}
                        })
                except Exception as e:
                    print(f"Failed to sync assignment subject for page {page['id']}: {e}")
        except Exception as e:
            print(f"Failed to query assignments for syncing subject: {e}")

    async def _reorder_sessions(self, db_id: str, student_page_id: str):
        if not db_id or not student_page_id: return
        
        try:
            response = await self.mcp.query_database(
                db_id,
                filter_payload={
                    "and": [
                        {"property": "🧑‍🎓 Students (학생 CRM)", "relation": {"contains": student_page_id}},
                        {"property": "Session Date", "date": {"is_not_empty": True}}
                    ]
                },
                sorts=[
                    {"property": "Session Date", "direction": "ascending"}
                ]
            )
            
            results = response.get("results", [])
            for idx, page in enumerate(results):
                current_title = ""
                try:
                    title_obj = page["properties"]["Session Title"]["title"]
                    if title_obj:
                        current_title = title_obj[0]["plain_text"]
                except KeyError:
                    pass
                
                expected_title = f"{idx + 1}차 멘토링"
                
                if current_title != expected_title:
                    print(f"🔄 자동 정렬(Self-Healing): '{current_title}' -> '{expected_title}' (Date: {page['properties']['Session Date']['date']['start']})")
                    await self.mcp.update_page(page["id"], {
                        "Session Title": {"title": [{"text": {"content": expected_title}}]}
                    })
        except Exception as e:
            print(f"Failed to reorder sessions: {e}")

    async def insert_global_review_queue(self, db_id: str, error_title: str, error_reason: str, raw_text: str):
        if not db_id: return
        from datetime import datetime
        now_iso = datetime.now().strftime("%Y-%m-%d")
        
        properties = {
            "Mail Title": {"title": [{"text": {"content": error_title[:100]}}]},
            "Error Reason": {"rich_text": [{"text": {"content": error_reason}}]},
            "Raw Email Text": {"rich_text": [{"text": {"content": raw_text[:2000]}}]},
            "Date": {"date": {"start": now_iso}}
        }
        try:
            await self.mcp.create_page(db_id, properties)
            print(f"⚠️ 에러 보관함(Review Queue)에 기록되었습니다: {error_title}")
        except Exception as e:
            print(f"Failed to insert into Review Queue: {e}")

    async def _insert_to_review_queue(self, db_id: str, session_data: ParsedMentoringSession):
        if not db_id: return
        # Since we use Global Review Queue, we will just use that logic.
        raw_text = ", ".join(session_data.mentorBrief.discussionPoints)
        await self.insert_global_review_queue(
            db_id,
            error_title=f"Low Confidence: Session {session_data.sessionNumber}",
            error_reason="확신도 낮음",
            raw_text=raw_text
        )

    async def _update_session(self, page_id: str, session_data: ParsedMentoringSession, student_page_id: str, raw_note: str = ""):
        summary_str = "\n".join(f"- {p}" for p in session_data.mentorBrief.discussionPoints)
        todo_str = "\n".join(f"- {a}" for a in session_data.mentorBrief.actionItems)
        
        meeting_link = session_data.mentorBrief.meetingLink
        raw_note_content = ""
        if meeting_link:
            raw_note_content += f"🔗 회의록 링크: {meeting_link}\n\n"
        if raw_note:
            raw_note_content += raw_note
        
        properties = {
            "Session Date": {"date": {"start": session_data.sessionDate}},
            "Meeting Summary": {"rich_text": parse_markdown_to_rich_text(summary_str)[:100]}, # API limit check roughly
            "Student to-do": {"rich_text": parse_markdown_to_rich_text(todo_str)[:100]},
            "One Sentence": {"rich_text": [{"text": {"content": getattr(session_data.mentorBrief, 'oneSentenceSummary', '')}}]}
        }
        if raw_note_content:
            properties["Raw Note"] = {"rich_text": parse_markdown_to_rich_text(raw_note_content[:2000])}
            
        try:
            await self.mcp.update_page(page_id, properties)
        except Exception as e:
            print(f"Failed to update session: {e}")

    async def _update_student_profile(self, student_page_id: str, mentor_brief):
        background_str = "\n".join(f"- {b}" for b in mentor_brief.backgroundContext)
        properties = {
            "Background": {"rich_text": parse_markdown_to_rich_text(background_str)[:100]},
            "Status": {"select": {"name": mentor_brief.trafficLightStatus}}
        }
        try:
            await self.mcp.update_page(student_page_id, properties)
            print(f"✅ Updated Student Profile (Background & Status)")
        except Exception as e:
            print(f"Failed to update student profile: {e}")

    async def _create_session(self, db_id: str, session_title: str, session_data: ParsedMentoringSession, student_page_id: str, raw_note: str = ""):
        summary_str = "\n".join(f"- {p}" for p in session_data.mentorBrief.discussionPoints)
        todo_str = "\n".join(f"- {a}" for a in session_data.mentorBrief.actionItems)
        
        meeting_link = session_data.mentorBrief.meetingLink
        raw_note_content = ""
        if meeting_link:
            raw_note_content += f"🔗 회의록 링크: {meeting_link}\n\n"
        if raw_note:
            raw_note_content += raw_note
        
        properties = {
            "Session Title": {"title": [{"text": {"content": session_title}}]},
            "Session Date": {"date": {"start": session_data.sessionDate}},
            "Meeting Summary": {"rich_text": parse_markdown_to_rich_text(summary_str)[:100]},
            "Student to-do": {"rich_text": parse_markdown_to_rich_text(todo_str)[:100]},
            "One Sentence": {"rich_text": [{"text": {"content": getattr(session_data.mentorBrief, 'oneSentenceSummary', '')}}]},
            "🧑‍🎓 Students (학생 CRM)": {"relation": [{"id": student_page_id}]}
        }
        if raw_note_content:
            properties["Raw Note"] = {"rich_text": parse_markdown_to_rich_text(raw_note_content[:2000])}
        
        if student_page_id:
            properties["🧑‍🎓 Students (학생 CRM)"] = {"relation": [{"id": student_page_id}]}
            
        try:
            return await self.mcp.create_page(db_id, properties)
        except Exception as e:
            print(f"Failed to create fallback session: {e}")
            return None

    async def _insert_insights(self, db_id: str, insights: list, student_page_id: str, session_page_id: str):
        for insight in insights:
            desc_str = insight_summary(insight)
            properties = {
                "Insight Title": {"title": [{"text": {"content": insight.insightTitle}}]},
                "Insight Type": {"select": {"name": insight.insightType}},
                "Summary": {"rich_text": plain_rich_text(desc_str)},
                "🧑‍🎓 Students (학생 CRM)": {"relation": [{"id": student_page_id}]},
                "💬 Mentoring Sessions": {"relation": [{"id": session_page_id}]}
            }
            try:
                await self.mcp.create_page(db_id, properties)
                print(f"✅ Inserted Insight: {insight.insightTitle}")
            except Exception as e:
                print(f"Failed to insert insight {insight.insightTitle}: {e}")
