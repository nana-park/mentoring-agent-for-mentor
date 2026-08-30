# 과거 코드 보관함 — 실행 대상 아님

현재 대시보드·파이프라인에서 사용하지 않거나, 현재 인터페이스와 맞지 않는 파일을 원문 그대로 보관합니다.
활성 코드에서 이 디렉터리를 import하지 않습니다. 오프라인 테스트 수집 대상도 아닙니다.
이동 당시의 import나 경로를 현행화하지 않았으므로 복원 없이 실행하면 안 됩니다.

| 파일 | 보관 이유 |
| --- | --- |
| `mcp_client.py` | 현재 구현은 Notion REST API 사용. 별도 MCP 의존성은 활성 코드에서 제거 |
| `brief_generator.py` | 현재 파이프라인에서 호출하지 않는 이전 브리핑 생성기 |
| `error_recovery.py` | 현재 파이프라인에서 호출하지 않는 복구 구현. 재처리 시 ingestion=None 전달 등 별도 검토 필요 |
| `mock_test.py`, `run_mock_runner.py` | 과거 run_pipeline 인자와 예전 패키지 경로 사용. 실제 오프라인 mock 테스트가 아님 |
| `test_google.py` | 현재 없는 fetch_latest_meeting_notes 메서드를 호출하는 과거 점검 파일 |
| `setup_notion_dbs.py` | 과거 DB 스키마와 문자 손상. 현행 초기 설정 도구로 사용 불가 |

필요한 기능을 다시 사용할 때는 현행 인터페이스·인증 경로·데이터 변경 범위를 검토해
`mentoring/` 또는 `scripts/`로 복원하고 테스트를 추가하세요.
