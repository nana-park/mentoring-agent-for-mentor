# Mentoring Agent for Mentor

**[GitHub Pages에서 화면 체험하기](https://nana-park.github.io/mentoring-agent-for-mentor/)**

공개 페이지는 가상 예시로 동작하는 **정적 데모**입니다. AI 분석·Gmail 조회·Notion 기록·예약 실행은 하지 않습니다.
입력은 현재 탭의 메모리에만 보관되고 새로고침하면 초기화됩니다. 실제 학생 정보·업무 기밀·인증정보는 입력하지 마세요.
실제 업무 처리는 아래 설치 방법으로 로컬 Flask 앱을 실행해야 합니다.

화면·문서 수정 후 `python scripts/build_pages.py`를 실행하고 `index.html`, `.nojekyll`, `pages-assets/`도 함께 커밋하세요.
Pages 게시 설정은 `main` 브랜치의 `/(root)`입니다. 빌더는 공개 템플릿·지정한 정적 파일·문서만 읽으며 인증·업무 파일은 읽거나 복사하지 않습니다.
데모 전용 동작은 `scripts/pages_demo.js`, 원본 업무 화면은 `mentoring/web/`에서 관리합니다.

멘토링 회의록을 Gemini로 분석하고 학생별 Notion CRM에 기록하는 로컬 웹 도구입니다.
Gmail의 Google Docs 링크, 로컬 텍스트 파일, 웹 직접 입력을 지원합니다.
학생 CRM 관리와 함께, 대화에서 멘토 본인의 AI 서비스 기획 업무에 유용한 발견·적용 가설을 추출합니다.

## 내 업무 맥락으로 서비스 적용 아이디어 얻기

대시보드 **개인 설정 → 내 업무 맥락 설정**에서 담당 서비스·목표와 ChatGPT에서 정리한 업무 메모를 등록합니다.
최신 내용인지 검토한 항목만 체크하고 전체 사용 설정을 켠 뒤 저장하세요.
맥락 사용은 기본 꺼짐이며 설정 저장 자체는 외부 API를 호출하지 않습니다.
ChatGPT 기록·메모리를 자동 동기화하지 않으며, 분석 시에는 승인한 맥락을 기존 **Gemini API**로 전달합니다.
결과는 근거 → 적용 서비스 → 작은 실험 → 판단 기준 → 조건·한계를 구분해 Notion에 기록합니다.
자세한 전송 범위와 시작 방법은 [멘토 인사이트 안내](docs/mentor_insights.md)를 참고하세요.

## 기존 사용자

`start_dashboard.bat`, `python app.py`, `python main.py --mode auto`,
`python run_auto.py`, `python run_batch.py`, `python summarize_insights.py`는 그대로 사용할 수 있습니다.
구현은 `mentoring/`으로 이동했지만 위 파일은 호환용 실행 진입점으로 유지합니다.

`.env`, `credentials.json`, `token.json`, `db_config.json`, `automation_config.json`,
`inbox/`, `archive/`는 **기존 프로젝트 루트에 그대로 둡니다.**
기존 `.env`를 예제 파일로 덮어쓰지 마세요. 파일 경로는 `mentoring/config.py`에서 관리합니다.

## 새 환경 설치

Python 3.12 기준으로 확인했습니다. 프로젝트 루트에서 다음을 실행합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env`에 `NOTION_TOKEN`, `GEMINI_API_KEY`를 입력합니다.
다른 Notion 워크스페이스라면 `NOTION_COURSES_DB_ID`, `NOTION_REVIEW_QUEUE_ID`도 지정하세요.
생략하면 기존 사용자의 DB ID를 유지합니다.
필요한 DB 속성과 관계는 [DB 스키마](docs/database_schema.md)를 참고하세요.
`legacy/setup_notion_dbs.py`는 과거 스키마용 보관 파일이므로 새 설치에 사용하지 않습니다.

Gmail 모드를 쓰려면 Google OAuth 클라이언트 설정을 루트의 `credentials.json`에 둡니다.
최초 인증 시 `token.json`이 생성됩니다. 두 파일과 `.env`는 Git에 올리지 않습니다.
웹 처리 이력 조회는 기존 루트 `db_config.json`의 `IngestionHistory` ID를 사용합니다.
이 파일이 없으면 처리 이력 화면은 오류를 안내하지만 대시보드는 열립니다.
`automation_config.json`은 예약 설정 저장 시 생성되며 기본값은 예약 꺼짐입니다.

## 실행

```powershell
.\.venv\Scripts\python.exe -m mentoring.web.app
.\.venv\Scripts\python.exe -m mentoring.cli --mode auto
.\.venv\Scripts\python.exe -m mentoring.cli --mode batch
.\.venv\Scripts\python.exe -m mentoring.cli --mode direct --payload "C:\path\to\session.json"
.\.venv\Scripts\python.exe -m mentoring.services.summarize_insights
```

웹 주소: `http://localhost:5000`. Windows에서는 `start_dashboard.bat`도 사용할 수 있습니다.
이 배치 파일은 `MENTORING_PYTHON` 환경변수 → 프로젝트 `.venv` → 사용자 Python 3.12 → PATH의 `python` 순서로 선택합니다.
다른 폴더에서 실행할 때는 루트의 `app.py`나 `main.py`를 절대 경로로 지정하세요.
`python -m ...`은 프로젝트 루트에서 실행합니다.

예약 작업은 **대시보드가 실행 중일 때만 로컬 batch 모드**를 수행합니다.
`python app.py` 또는 `python -m mentoring.web.app`으로 시작하세요.
`flask --app app run`으로는 예약 스레드가 시작되지 않습니다.
중복 스케줄러를 피하기 위해 개발용 자동 재시작은 꺼져 있습니다.

## 문서와 코드

- [문서 안내](docs/README.md): 어떤 문서를 어디서 관리하는지
- [파일 구조와 경로 규칙](docs/project_structure.md): 폴더 트리, 이동표, 실행 경로
- [시스템 구조도](docs/architecture_diagram.md): 모듈과 데이터 흐름
- [DB 스키마](docs/database_schema.md): Notion 필드와 관계
- [알려진 제한](docs/known_limitations.md): 이번 구조 정리와 분리된 기존 동작 문제
- [운영 스크립트](scripts/README.md): 점검과 데이터 수정 작업 구분
- [보관 코드](legacy/README.md): 사용하지 않는 과거 구현

## 오프라인 검증

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

경로, 웹 문서/정적 파일, CLI, 프로세스 실행 명령을 외부 API 없이 검증합니다.
실제 Gmail 수집, Gemini 호출, Notion 쓰기는 수행하지 않습니다.
실제 처리 버튼은 학생 정보를 Gemini에 전송하고 Notion을 변경하므로 운영 데이터로 가볍게 시험하지 마세요.
