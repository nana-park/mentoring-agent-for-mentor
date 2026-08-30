import json
from google import genai
from google.genai import types

class ErrorRecoveryHandler:
    def __init__(self, notion_mcp, global_review_queue_id: str, parser, upsert, process_source_fn, course_map: dict):
        self.mcp = notion_mcp
        self.queue_id = global_review_queue_id
        self.parser = parser
        self.upsert = upsert
        self.process_source = process_source_fn
        self.course_map = course_map

    async def run_recovery(self):
        print("🛠️ 자가 치유(Self-Healing) 프로세스 시작...")
        if not self.queue_id:
            print("글로벌 리뷰 큐 ID가 없습니다. 스킵합니다.")
            return

        try:
            response = await self.mcp.query_database(
                self.queue_id,
                filter_payload={
                    "and": [
                        {
                            "property": "Human Feedback",
                            "rich_text": {"is_not_empty": True}
                        },
                        {
                            "property": "Error Fix Trial",
                            "checkbox": {"equals": False}
                        }
                    ]
                }
            )
            results = response.get("results", [])
            if not results:
                print("✅ 피드백이 새로 추가된(미처리된) 에러 항목이 없습니다.")
                return

            print(f"총 {len(results)}개의 새로운 피드백 항목 재시도를 시작합니다.")
            
            for page in results:
                await self._process_recovery_item(page)
                
        except Exception as e:
            print(f"Error during self-healing: {e}")

    async def _process_recovery_item(self, page: dict):
        page_id = page["id"]
        props = page["properties"]
        
        # Extract properties
        mail_title_prop = props.get("Mail Title", {})
        mail_title = mail_title_prop.get("title", [{"plain_text": ""}])[0].get("plain_text", "") if mail_title_prop.get("title") else ""
        
        raw_text_prop = props.get("Raw Email Text", {})
        raw_text = raw_text_prop.get("rich_text", [{"plain_text": ""}])[0].get("plain_text", "") if raw_text_prop.get("rich_text") else ""
        
        feedback_prop = props.get("Human Feedback", {})
        human_feedback = feedback_prop.get("rich_text", [{"plain_text": ""}])[0].get("plain_text", "") if feedback_prop.get("rich_text") else ""
        
        print(f"\n[복구 시도] 메일 제목: '{mail_title}'")
        print(f"강사님 피드백: '{human_feedback}'")
        
        if not raw_text:
            print("원본 메일 텍스트가 없어서 복구할 수 없습니다.")
            await self._mark_trial_completed(page_id)
            return
            
        # 1. Ask LLM to extract the exact alias used in the raw email, based on the Human Feedback.
        alias_to_learn = await self._extract_alias_from_feedback(raw_text, human_feedback)
        
        student_name_to_update = None
        # Try to find the student mentioned in the human feedback
        if alias_to_learn and alias_to_learn != "UNKNOWN":
            print(f"💡 AI 추론 별명/오타 발견: '{alias_to_learn}'")
            # We need to find which student this belongs to. Let LLM guess the correct student name from the course_map
            student_name_to_update = await self._guess_student_from_feedback(human_feedback)
            
            if student_name_to_update:
                await self._update_student_alias(student_name_to_update, alias_to_learn)
        
        # 2. Re-process the email with Human Feedback injected into the subject or text to force match
        enhanced_text = f"=== HUMAN FEEDBACK / HINT ===\n{human_feedback}\n==========================\n\n{raw_text}"
        
        try:
            # We mock ingestion layer since it's a retry
            await self.process_source(
                source_text=enhanced_text,
                source_id=page_id, # Use page_id as mock source_id
                subject=mail_title,
                source_type="Error Queue Retry",
                ingestion=None, 
                parser=self.parser, 
                upsert=self.upsert,
                course_map=self.course_map, 
                notion_mcp=self.mcp,
                global_review_queue_id=self.queue_id
            )
            
            # 3. Clean up (delete the error row)
            await self.mcp.client.patch(f"/pages/{page_id}", json={"archived": True})
            print(f"🗑️ 복구 성공! 큐에서 항목을 삭제(Archive)했습니다.")
            
        except Exception as e:
            print(f"❌ 복구 실패: {e}")
            # Mark the trial as completed so we don't loop endlessly
            await self._mark_trial_completed(page_id)

    async def _mark_trial_completed(self, page_id: str):
        try:
            await self.mcp.update_page(page_id, {
                "Error Fix Trial": {"checkbox": True}
            })
            print("✅ 복구 시도(Error Fix Trial) 체크박스를 체크했습니다.")
        except Exception as e:
            print(f"Failed to check Error Fix Trial box: {e}")

    async def _extract_alias_from_feedback(self, raw_text: str, human_feedback: str):
        prompt = f"""
        [원본 이메일 텍스트]
        {raw_text[:2000]}
        
        [강사님 피드백]
        {human_feedback}
        
        강사님이 피드백을 통해 이 메일이 특정 학생의 것이라고 알려주셨습니다.
        이메일 원본 텍스트를 분석해서, 이 이메일 내에서 그 학생을 지칭하기 위해 사용된 '잘못된 이름(오타)'이나 '별명/영어 이름'이 정확히 무엇인지 하나만 추출하세요.
        추출할 수 없으면 UNKNOWN 이라고 답하세요.
        단답형으로 추출한 별명만 답하세요.
        """
        response = self.parser.client.models.generate_content(model='gemini-2.5-pro', contents=prompt)
        return response.text.strip()
        
    async def _guess_student_from_feedback(self, human_feedback: str):
        students_list = []
        for cname, cdata in self.course_map.items():
            for st in cdata["students"]:
                students_list.append(st['name'])
                
        prompt = f"""
        [강사님 피드백]
        {human_feedback}
        
        [전체 학생 목록]
        {students_list}
        
        강사님 피드백에서 언급된 학생의 정확한 본명(전체 학생 목록에 있는 이름)을 추출하세요.
        목록에 없거나 확신할 수 없으면 빈 문자열을 반환하세요.
        단답형으로 이름만 답하세요.
        """
        response = self.parser.client.models.generate_content(model='gemini-2.5-pro', contents=prompt)
        name = response.text.strip()
        return name if name in students_list else None

    async def _update_student_alias(self, student_name: str, new_alias: str):
        # Find student page id
        student_page_id = None
        current_alias = ""
        for cname, cdata in self.course_map.items():
            for st in cdata["students"]:
                if st["name"] == student_name:
                    student_page_id = st["page_id"]
                    current_alias = st.get("alias", "")
                    break
            if student_page_id: break
            
        if not student_page_id: return
        
        # Append new alias if not exists
        if new_alias in current_alias:
            return
            
        updated_alias = f"{current_alias}, {new_alias}".strip(", ")
        
        try:
            await self.mcp.update_page(student_page_id, {
                "Alias": {"rich_text": [{"text": {"content": updated_alias}}]}
            })
            print(f"🎓 학생 DB 업데이트 완료! ({student_name}의 별명 추가: {new_alias})")
            
            # Update memory course_map for this run
            for cname, cdata in self.course_map.items():
                for st in cdata["students"]:
                    if st["name"] == student_name:
                        st["alias"] = updated_alias
                        break
        except Exception as e:
            print(f"Failed to update student alias: {e}")
