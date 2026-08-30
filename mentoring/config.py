"""Paths are anchored to the checkout, never to the process working directory."""
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
DB_CONFIG_FILE = PROJECT_ROOT / "db_config.json"
AUTOMATION_CONFIG_FILE = PROJECT_ROOT / "automation_config.json"
GOOGLE_TOKEN_FILE = PROJECT_ROOT / "token.json"
GOOGLE_CREDENTIALS_FILE = PROJECT_ROOT / "credentials.json"
INBOX_DIR = PROJECT_ROOT / "inbox"
ARCHIVE_DIR = PROJECT_ROOT / "archive"
DOCS_DIR = PROJECT_ROOT / "docs"
DIAGNOSTICS_DIR = PROJECT_ROOT / "runtime" / "diagnostics"
WEB_DIR = PROJECT_ROOT / "mentoring" / "web"
MENTOR_CONTEXT_FILE = PROJECT_ROOT / "runtime" / "mentor_context.json"


def load_environment():
    return load_dotenv(ENV_FILE, override=False)


def course_database_id():
    # Preserve the existing workspace unless explicitly overridden in .env.
    return os.getenv("NOTION_COURSES_DB_ID") or "358c919e-34d1-80f0-9573-edb4e42a261a"


def review_queue_id():
    return os.getenv("NOTION_REVIEW_QUEUE_ID") or "374c919e-34d1-8040-ab19-d3ac7d73e526"


def diagnostic_output(filename):
    if Path(filename).name != filename:
        raise ValueError("Expected a filename, not a path")
    DIAGNOSTICS_DIR.mkdir(parents=True, exist_ok=True)
    return DIAGNOSTICS_DIR / filename
