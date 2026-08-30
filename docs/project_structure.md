# 파일 구조와 경로 규칙

```text
mentoring-agent-for-mentor/
├─ README.md
├─ requirements.txt
├─ .env.example
├─ app.py / main.py                   # 기존 실행 명령 호환
├─ run_auto.py / run_batch.py         # 기존 실행 명령 호환
├─ summarize_insights.py              # 기존 실행 명령 호환
├─ start_dashboard.bat
├─ mentoring/
│  ├─ config.py                       # 루트 기준 경로·환경 설정
│  ├─ cli.py / __main__.py            # 명령행 진입점
│  ├─ pipeline.py / models.py
│  ├─ integrations/                   # Notion·Google 연결
│  ├─ services/                       # 분석·조회·기록·요약
│  └─ web/
│     ├─ app.py                       # HTTP 요청
│     ├─ processes.py                 # 실행 명령·로그
│     ├─ scheduler.py                 # 예약 설정·실행
│     ├─ templates/
│     └─ static/
├─ scripts/
│  ├─ diagnostics/                    # 조회·진단
│  └─ maintenance/                    # 실제 데이터 수정
├─ tests/                            # 외부 API 없는 검증
├─ legacy/                           # 과거 코드, 실행 대상 아님
├─ docs/
│  ├─ README.md
│  ├─ project_structure.md            # 이 문서: 파일 위치
│  ├─ architecture_diagram.md         # 실행 흐름 구조도
│  ├─ database_schema.md              # DB 필드·관계
│  ├─ known_limitations.md
│  ├─ snapshots/                      # 과거 DB 진단 결과
│  └─ archive/                        # 이전 구조 설명
├─ .env                              # 로컬 전용, 기존 위치 유지
├─ credentials.json / token.json     # 로컬 전용, 기존 위치 유지
├─ db_config.json                    # 로컬 전용, 기존 위치 유지
├─ automation_config.json            # 로컬 전용, 기존 위치 유지
├─ inbox/ / archive/                 # 로컬 전용, 기존 위치 유지
└─ runtime/diagnostics/               # 새 진단 출력, Git 제외
```

## 경로를 안전하게 관리하는 방법

1. 앱의 파일은 `mentoring/config.py`에서 정의한 절대 경로를 사용합니다.
   `Path(__file__).resolve().parent.parent`로 프로젝트 루트를 한 번 계산합니다.
2. 다른 모듈이 자기 파일 위치로 `.env`나 `inbox/`를 찾지 않습니다.
3. Python 내부 참조는 `from mentoring.services... import ...`처럼 패키지 전체 경로를 씁니다.
4. 웹 하위 프로세스는 현재 Python 인터프리터의 `-m` 모듈 명령을 사용하고 cwd를 프로젝트 루트로 고정합니다.
5. 배치 파일은 `%~dp0`로 자신의 폴더를 찾아갑니다. 특정 사용자 이름을 하드코딩하지 않습니다.
6. `--payload`는 사용자가 지정한 경로를 그대로 받습니다. CLI의 상대 경로는 사용자의 실행 폴더 기준입니다.
   웹은 임시 파일의 절대 경로를 전달하고 종료 시 삭제합니다.

루트의 실행 호환 파일만 외부에서 직접 실행하세요. `mentoring/pipeline.py`를 파일 경로로 직접 실행하는 대신
프로젝트 루트에서 `python -m mentoring.cli --mode batch`를 사용합니다.
운영 스크립트는 모듈 실행을 권장하며, 직접 파일 실행도 루트를 계산하여 지원합니다.

`.env`와 인증 파일은 이동하지 않았으며 내용도 변경하지 않았습니다.
환경변수가 이미 설정되어 있으면 `.env`보다 우선합니다.
진단 코드의 과거 대상 DB ID와 legacy의 과거 경로는 현행 앱 경로와 구분합니다.

## 이전 위치 → 현재 위치

최상위 `app.py`, `main.py`, `summarize_insights.py`는 구현이 이동한 뒤 짧은 실행 연결 파일로 남습니다.
`run_auto.py`, `run_batch.py`도 유지되며 웹 실행 시 엔터 입력을 기다리지 않습니다.

| 이전 파일 | 현재 구현 / 보관 위치 |
| --- | --- |
| `main.py` | `mentoring/pipeline.py` |
| `app.py` | `mentoring/web/app.py` |
| `models.py` | `mentoring/models.py` |
| `notion_api.py` | `mentoring/integrations/notion.py` |
| `google_api_client.py` | `mentoring/integrations/google_workspace.py` |
| `mcp_client.py` | `legacy/mcp_client.py` |
| `brief_generator.py` | `legacy/brief_generator.py` |
| `mock_test.py` | `legacy/mock_test.py` |
| `run_mock_runner.py` | `legacy/run_mock_runner.py` |
| `test_google.py` | `legacy/test_google.py` |
| `setup_notion_dbs.py` | `legacy/setup_notion_dbs.py` |
| `error_recovery.py` | `legacy/error_recovery.py` |
| `backfill_one_sentence.py` | `scripts/maintenance/backfill_one_sentence.py` |
| `check_schema.py` | `scripts/maintenance/check_schema.py` |
| `test.py` | `scripts/diagnostics/inspect_course_children.py` |
| `test_queries.py` | `scripts/diagnostics/check_queries.py` |
| `batch_processor.py` | `mentoring/services/batch_processor.py` |
| `ingestion_tracker.py` | `mentoring/services/ingestion_tracker.py` |
| `llm_parser.py` | `mentoring/services/llm_parser.py` |
| `loaders.py` | `mentoring/services/loaders.py` |
| `upsert.py` | `mentoring/services/upsert.py` |
| `summarize_insights.py` | `mentoring/services/summarize_insights.py` |
| `check_db.py` | `scripts/diagnostics/check_db.py` |
| `check_env.py` | `scripts/diagnostics/check_env.py` |
| `check_notion.py` | `scripts/diagnostics/check_notion.py` |
| `debug_db.py` | `scripts/diagnostics/debug_db.py` |
| `dump_error_schema.py` | `scripts/diagnostics/dump_error_schema.py` |
| `dump_ingestion_schema.py` | `scripts/diagnostics/dump_ingestion_schema.py` |
| `find_db.py` | `scripts/diagnostics/find_db.py` |
| `search_dbs.py` | `scripts/diagnostics/search_dbs.py` |
| `db_schema_output.txt` | `docs/snapshots/db_schema_output.txt` |
| `error_queue_schema.txt` | `docs/snapshots/error_queue_schema.txt` |
| `ingestion_schema.txt` | `docs/snapshots/ingestion_schema.txt` |
| `templates/index.html` | `mentoring/web/templates/index.html` |
| `static/images/breadme_logo.png` | `mentoring/web/static/images/breadme_logo.png` |
| `static/images/breadme_logo.svg` | `mentoring/web/static/images/breadme_logo.svg` |
| `static/images/file_explorer.svg` | `mentoring/web/static/images/file_explorer.svg` |

## 변경 검증

프로젝트 루트에서 `python -m unittest discover -s tests -v`를 실행하세요.
테스트는 다른 작업 폴더에서도 설정·문서·이미지를 찾는지, CLI와 웹 실행 명령이 올바른 모듈과 payload를
전달하는지 확인합니다. 인증 파일 내용과 실제 학생 원문은 사용하지 않습니다.
