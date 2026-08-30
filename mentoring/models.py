from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class MentorInsight(BaseModel):
    insightTitle: str = Field(max_length=160, description="Reusable discovery or application hypothesis for the mentor")
    insightType: Literal["기획 실무", "교육 개선", "학습 태도 및 동기", "취업 및 진로 고민"] = Field(description="Category of the insight")
    description: List[str] = Field(description="Why this is useful to the mentor's own work, not a student evaluation")
    insightKind: Literal["대화 기반 발견", "업무 적용 가설"] = Field(default="대화 기반 발견")
    evidenceQuotes: List[str] = Field(default_factory=list, max_length=3, description="Exact short quotes copied from the meeting transcript")
    targetServiceId: str = Field(default="", max_length=80)
    targetService: str = Field(default="", max_length=120, description="Server-populated service name; return empty")
    contextRefs: List[str] = Field(default_factory=list, max_length=20)
    applicability: str = Field(default="", max_length=2000)
    nextExperiment: str = Field(default="", max_length=2000)
    successCriterion: str = Field(default="", max_length=2000)
    caveats: str = Field(default="", max_length=2000)
    mentorContextVersion: str = Field(default="", max_length=64, description="Server-populated; return empty")

class RoutingDecision(BaseModel):
    matchedCourse: str = Field(description="Matched Course ID or Name")
    matchedStudent: str = Field(description="Matched Student ID or Name")
    confidence: float = Field(description="Confidence score between 0 and 1")
    matchingReason: str = Field(description="Reason for matching")
    needsHumanReview: bool = Field(description="True if confidence is low")

class MentorBrief(BaseModel):
    backgroundContext: List[str] = Field(description="Background of the student. Must include categories formatted as 'Category: Description' (e.g., '현재 직업: 교직원', '본전공: 기계공학')")
    trafficLightStatus: Literal["🟢 정상 진행", "🟡 과제 지연", "🔴 이탈 위험", "⭐ 우수 수강생"] = Field(description="Current status")
    warningSignals: List[str] = Field(description="List of warning signals if any")
    pastAssignmentStatus: str = Field(description="Status of previous assignments")
    assignmentSubject: Optional[str] = Field(default=None, description="The subject or topic of the student's assignment if mentioned")
    meetingLink: Optional[str] = Field(default=None, description="URL or link to the meeting notes if present in the raw text")
    discussionPoints: List[str] = Field(description="Points to discuss next")
    oneSentenceSummary: str = Field(description="1-2 sentence summary of the entire meeting")
    actionItems: List[str] = Field(description="Action items for student")

class ParsedMentoringSession(BaseModel):
    sessionDate: str = Field(description="Date of the session YYYY-MM-DD")
    sessionNumber: int = Field(description="Session number e.g. 1, 2")
    routing: RoutingDecision
    mentorBrief: MentorBrief
    assignmentTitle: Optional[str] = Field(description="Title of the assignment given")
    submissionStatus: Literal["Not Started", "In Progress", "Submitted", "Revised"] = Field(description="Status of the assignment")
    mentorInsights: Optional[List[MentorInsight]] = Field(description="Any insights gathered by the mentor")
