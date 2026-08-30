import os
import json
from google import genai
from google.genai import types
from models import ParsedMentoringSession

class LLMParser:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key)

    async def identify_context(self, source_text: str, source_subject: str, active_courses: list, students_list: list):
        prompt = f"""
        당신은 멘토링 회의록과 제목을 분석하여, 이 세션이 어떤 강의의 어떤 학생과 진행된 것인지 찾아내는 역할입니다.
        
        [입력 데이터]
        - 제목: {source_subject}
        - 본문: {source_text[:1000]} # 첫 1000자만 제공
        
        [현재 활성화된 강의 목록]
        {active_courses}
        
        [전체 학생 목록 (이름 (강의명) - 별명/오타: xxx - 관련 주제/배경: yyy)]
        {students_list}
        
        위 데이터를 바탕으로 가장 확률이 높은 학생 이름(student_name)과 강의명(course_name)을 추출하세요.
        - [최우선 조건]: 본문이나 제목에 학생의 '별명/오타(Alias)'와 정확히 일치하거나 포함되는 단어가 있다면 (예: 영어 닉네임, 아이디 등), 다른 문맥을 무시하고 무조건 그 학생을 선택하세요.
        - 이름이 없거나 애매한 경우, 본문의 프로젝트 주제/내용이 학생의 '관련 주제/배경'과 가장 일치하는 학생을 추리(Fuzzy Match)하여 선택하세요.
        - 도저히 확신할 수 없거나 목록에 일치하는 학생이 없다면 빈 문자열을 반환하세요.
        - [중요]: 만약 본문 내에 학생 목록에 존재하는 학생이 **2명 이상** 등장하거나, 명백히 여러 학생의 피드백이 섞인 통합 회의록이라고 판단된다면 `multiple_students_detected`를 true로 설정하세요. 그렇지 않으면 false로 설정하세요.
        """
        
        from pydantic import BaseModel
        class ContextMatch(BaseModel):
            student_name: str
            course_name: str
            multiple_students_detected: bool
            
        response = self.client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ContextMatch,
            ),
        )
        try:
            return json.loads(response.text)
        except Exception:
            return {"student_name": "", "course_name": "", "multiple_students_detected": False}

    async def parse_mentoring_data(self, source_text: str, source_subject: str, student_name: str, course_name: str, historical_context: list, existing_background: str = ""):
        prompt = f"""
        학생 '{student_name}' (강의: '{course_name}')의 멘토링 세션 데이터를 분석하세요.
        
        [메일 제목 / 메타데이터]
        {source_subject}
        (위 제목에서 세션 날짜를 유추할 수 있습니다. 본문에 날짜가 없다면 이 제목의 날짜를 사용하세요.)
        
        [회의록 전문]
        {source_text}
        
        [이전 세션 히스토리 (참고용)]
        {historical_context}
        
        [기존 학생 백그라운드]
        {existing_background}
        
        [지시사항]
        - 멘토링에서 논의된 주요 내용을 추출하여 `discussionPoints` 리스트로 만드세요.
          [중요 지시사항]: 만약 입력된 텍스트가 타임스탬프와 불릿포인트 등으로 **이미 상세하게 요약된 회의록(예: 클로바노트)** 이라면, 내용을 절대 임의로 축약하거나 생략하지 말고 **원문의 디테일을 100% 살려서 그대로 불릿포인트로 추출**하세요. 반면, 요약되지 않은 날것의 대화 스크립트라면 핵심 논의 사항을 요약해서 추출하세요.
          [서식 지시사항]: 불릿포인트 문장 중에 `키워드: 내용` 형식으로 작성되는 항목이 있다면, 반드시 콜론(`:`)까지 포함하여 앞부분을 마크다운 굵게(Bold) 처리하세요. (예: `**목표:** 서비스 기획 고도화`, `**[김채원] 벤치마킹 조사:** 다른 쇼핑몰의 고객 정보...`)
        - `discussionPoints` 작성이 완료되면, 해당 미팅의 전체적인 핵심 내용을 두 문장 이내로 압축하여 `oneSentenceSummary`에 작성하세요.
        - 회의록 원문에 클로바노트, 줌(Zoom), 구글 미트 등 **회의록이나 영상의 공유 링크(URL)** 가 포함되어 있다면 `meetingLink`로 추출하세요. 없다면 null로 처리하세요.
        - 학생의 전공, 서비스기획 경험, 앞으로 어떤 업무를 진행하고 싶은지 등 학생의 전반적인 백그라운드 정보를 추출하여 `backgroundContext` 리스트를 구성하세요. 
          반드시 [기존 학생 백그라운드] 내용에 이번 회의록에서 새롭게 파악된 배경 정보만 추가하여, 중복 없이 완벽히 통합된 하나의 리스트로 완성하세요.
          반드시 아래의 [표준 카테고리] 중 언급된 항목만 골라서 '카테고리명: 내용' 형태의 정형화된 포맷을 따르세요. 언급되지 않은 카테고리는 생략해도 좋으며, 그 외 특징은 카테고리명 없이 바로 내용만 적어주세요 (예: '사람 만나는 직무에 흥미').
          [표준 카테고리]: '현재 직업', '본전공', '복수전공', '과거 이력 및 경험', '서비스기획에 대한 관심도 및 목표'
          예시) "현재 직업: 학교 교직원으로 재직 중", "본전공: 기계공학", "과거 이력 및 경험: 마케팅 및 콘텐츠 기획 경험 보유", "사람 만나는 직무에 흥미"
        - 학생의 현재 상태(`trafficLightStatus`)를 회의록 뉘앙스를 바탕으로 ['🟢 정상 진행', '🟡 과제 지연', '🔴 이탈 위험', '⭐ 우수 수강생'] 중 하나로 판단하세요.
        - 학생이 진행 중인 과제의 주제(Subject)가 구체적으로 언급되었다면 `assignmentSubject`로 추출하세요. 명확하지 않거나 언급되지 않았다면 null로 처리하세요.
        
        주어진 JSON 스키마에 맞게 세션 날짜, 요약, 과제, 멘토 인사이트 등을 추출하세요.
        """
        response = self.client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ParsedMentoringSession,
            ),
        )
        return ParsedMentoringSession.model_validate_json(response.text)

    async def split_text_by_students(self, text: str) -> list[dict]:
        prompt = """
        다음은 멘토링 세션 또는 회의록의 내용입니다.
        이 내용이 한 명의 학생에 대한 것인지, 여러 명의 학생에 대한 것인지 파악하여, 각 학생별로 관련된 내용을 분리해주세요.
        만약 텍스트가 여러 학생을 다루고 있다면 배열에 여러 객체를 넣고, 한 명만 다룬다면 한 개의 객체만 넣으세요.
        원문의 내용을 누락하거나 요약하지 말고, 해당 학생에게 해당하는 부분(요약, 다음 단계, 상세 정보 등)을 모두 모아서 'content'에 그대로 담아주세요.
        
        [중요 주의사항]
        - 작성자(멘토)의 이름이나 멘토 본인(예: 박나현, Nahyun Park, Nahyun 등)은 학생으로 추출하지 마세요.
        - 오직 멘토링 피드백을 '받는' 실제 대상(학생)만 이름(name)으로 추출해야 합니다.
        - 실제 학생이 아닌 사람이나 단순히 언급된 강사/멘토 이름이 배열에 추가되지 않도록 각별히 주의하세요.
        """
        
        from pydantic import BaseModel
        class StudentChunk(BaseModel):
            name: str
            content: str
            
        class SplitResult(BaseModel):
            students: list[StudentChunk]
            
        response = self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt + f"\n\n[원본 텍스트]\n{text}",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SplitResult,
            ),
        )
        try:
            res = json.loads(response.text)
            return res.get("students", [])
        except Exception:
            return [{"name": "Unknown", "content": text}]
