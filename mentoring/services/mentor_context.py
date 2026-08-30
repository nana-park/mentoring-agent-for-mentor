"""User-reviewed work context. Local storage only; model use is explicitly opt-in."""
import json
import os
from pathlib import Path
import tempfile
import threading
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator
from mentoring.config import MENTOR_CONTEXT_FILE

CONTEXT_FILE = MENTOR_CONTEXT_FILE
_lock = threading.Lock()


class ServiceContext(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    id: str = Field(default_factory=lambda: 'svc-' + uuid4().hex, pattern=r'^svc-[a-zA-Z0-9-]{1,64}$')
    name: str = Field(min_length=1, max_length=120)
    details: str = Field(min_length=1, max_length=3000, description='Users, AI features, stage, goals and constraints')
    approved: bool = False


class ContextNote(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    id: str = Field(default_factory=lambda: 'ctx-' + uuid4().hex, pattern=r'^ctx-[a-zA-Z0-9-]{1,64}$')
    title: str = Field(min_length=1, max_length=160)
    source: str = Field(default='직접 입력', max_length=160)
    text: str = Field(min_length=1, max_length=12000)
    approved: bool = False


class MentorContext(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    revision: str = Field(default='', max_length=64)
    enabled: bool = False
    role: str = Field(default='AI 서비스 기획자', max_length=300)
    goals: str = Field(default='', max_length=3000)
    services: list[ServiceContext] = Field(default_factory=list, max_length=8)
    notes: list[ContextNote] = Field(default_factory=list, max_length=12)

    @model_validator(mode='after')
    def check_budget_and_ids(self):
        ids = [item.id for item in [*self.services, *self.notes]]
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate context IDs')
        if len(self.model_dump_json()) > 50000:
            raise ValueError('Context exceeds 50,000 character budget; summarize first')
        return self


class ContextConflict(ValueError):
    pass


def load_context():
    if not CONTEXT_FILE.exists():
        return MentorContext()
    # Corrupted context is surfaced to the UI; never silently overwrite it.
    return MentorContext.model_validate_json(CONTEXT_FILE.read_text(encoding='utf-8'))


def save_context(data):
    context = MentorContext.model_validate(data)
    with _lock:
        if context.revision != load_context().revision:
            raise ContextConflict('Context changed; reload before saving')
        context.revision = uuid4().hex
        CONTEXT_FILE.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=CONTEXT_FILE.parent,
                                             prefix='.mentor-context-', delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(context.model_dump_json(indent=2))
            os.replace(temporary, CONTEXT_FILE)
        finally:
            if temporary and temporary.exists():
                temporary.unlink()
    return context


def delete_context(revision):
    with _lock:
        if revision != load_context().revision:
            raise ContextConflict('Context changed; reload before deleting')
        CONTEXT_FILE.unlink(missing_ok=True)


def approved_context(context=None):
    if context is None:
        try:
            context = load_context()
        except (ValueError, OSError):
            print('업무 맥락 파일을 읽을 수 없어 이번 분석에서는 사용하지 않습니다.')
            return {}
    if not context.enabled:
        return {}
    return {
        'revision': context.revision,
        'role': context.role,
        'goals': context.goals,
        'services': [s.model_dump(exclude={'approved'}) for s in context.services if s.approved],
        'notes': [n.model_dump(exclude={'approved'}) for n in context.notes if n.approved],
    }


def context_json(context):
    return json.dumps(context, ensure_ascii=False) if context else '업무 맥락 사용 꺼짐. 멘토의 실제 서비스는 알 수 없음.'
