# 운영 스크립트

프로젝트 루트에서 `python -m scripts.<분류>.<파일명>`으로 실행합니다.
직접 파일 경로로 실행하는 방식도 지원합니다. 모든 활성 스크립트는 루트의 `.env`를 사용합니다.

## diagnostics: 조회·진단

- `check_env`: API 키의 존재 여부만 출력합니다. 키 내용은 출력하지 않습니다.
- `check_db`, `debug_db`, `find_db`, `search_dbs`: 기존 특정 DB를 조회합니다.
- `inspect_course_children`: 이전 `test.py`; 강의 내부 DB 구조를 조회합니다.
- `check_queries`: 이전 `test_queries.py`; 이력·검토 큐 조회를 확인합니다.
- `check_notion`, `dump_error_schema`, `dump_ingestion_schema`: DB 구조를 조회하여
  `runtime/diagnostics/`에 결과를 저장합니다.

`check_env` 외에는 외부 Notion API를 호출합니다.
일부 진단 대상 ID는 기존 작업 대상 그대로 고정되어 있으므로 다른 워크스페이스에서 실행 전 코드를 확인하세요.

## maintenance: 실제 데이터 수정

- `backfill_one_sentence`: 기존 멘토링 요약을 Gemini로 처리하여 Notion의 One Sentence를 수정합니다.
- `check_schema`: 이름은 점검이지만 **특정 Notion 페이지의 One Sentence를 시험 값으로 덮어씁니다.**

이 스크립트들은 테스트가 아닙니다. 대상 DB·페이지와 변경 내용을 검토한 후 수동 실행하세요.
대시보드나 오프라인 테스트에서 자동 호출하지 않습니다.

## 초기 설정과 보관 코드

기존 `setup_notion_dbs.py`는 현재 DB 스키마와 다른 과거 버전이며 문자 손상도 있어
`legacy/`에 보관했습니다. 이번 정리에서 DB 생성 도구로 재사용하거나 실행하지 않았습니다.
현재 설치에는 `docs/database_schema.md`와 기존 Notion 템플릿을 참고하세요.
