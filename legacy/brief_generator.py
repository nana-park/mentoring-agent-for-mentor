from google import genai

class MentorBriefGenerator:
    def __init__(self):
        self.client = genai.Client()
        self.model_name = "gemini-2.5-flash" # Flash is fast enough for summarization
        
    def generate_brief(self, student_background: str, status_and_risks: str, historical_context: str, current_assignments: str) -> str:
        """
        Generates a 1-minute follow-up briefing for the Mentor before the session starts.
        """
        prompt = f"""
        You are generating a "1-Minute Mentor Brief" for a Mentor about to jump into a 1:1 session with a student.
        Your goal is to give the mentor immediate context, highlight risks, and suggest exact questions to ask based on Assignment progress.
        
        [Input Data]
        Student Background: {student_background}
        Status & Risks: {status_and_risks}
        Recent Mentoring History: {historical_context}
        Current Assignments: {current_assignments}
        
        [Output Format Required]
        Output must strictly follow this Markdown structure:
        
        ### ?뫅?랅윃??숈깮 諛곌꼍
        (Summarize background in 1 line)
        
        ### ?슚 ?곹깭 諛??꾪뿕 ?좏샇
        (E.g., ?뵶?댄깉 ?꾪뿕 / 2二??곗냽 怨쇱젣 誘몄젣異? 紐⑺몴 蹂寃?怨좊?以?
        
        ### ?뱷 吏??怨쇱젣 ?꾪솴
        (E.g., ?쒕굹由ъ삤 ?묒꽦 ?꾨즺, ?ㅼ씠?닿렇??誘몄젣異?
        
        ### ?뿣截??ㅼ쓬 ?몄뀡 ?쒖옉 吏덈Ц (Recommended)
        (E.g., "吏??怨쇱젣 吏꾪뻾?섎㈃???꾩씠?붿뼱媛 ?대뼸寃?諛붾뚯뿀?섏슂?")
        
        ### ?뵇 ?뺤씤 ?ъ씤??        - (Point 1)
        - (Point 2)
        """
        
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )
        
        return response.text
