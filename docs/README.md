# 문서 안내

문서를 코드 옆의 `docs/`에서 관리합니다. 구조도를 별도의 이미지 파일로만 보관하지 않고,
Markdown 안의 Mermaid 원문을 기준으로 유지합니다. GitHub와 대시보드에서 같은 원문을 읽습니다.

| 문서 | 역할 | 갱신 시점 |
| --- | --- | --- |
| `project_structure.md` | 물리적인 폴더·파일 위치, 경로 규칙, 이전 위치 매핑 | 파일 이동·진입점 변경 시 |
| `architecture_diagram.md` | 실행 흐름과 모듈 책임 | 모듈 연결·처리 흐름 변경 시 |
| `database_schema.md` | Notion DB 필드와 관계 | DB 속성이나 쓰기 코드 변경 시 |
| `known_limitations.md` | 확인된 제한 및 후속 개선점 | 해당 문제를 수정하고 검증했을 때 |
| `snapshots/` | 과거 DB 점검 명령의 결과 | 역사적 참고용; 최신 스키마로 간주하지 않음 |
| `archive/` | 이전 구조 설명 보관 | 현재 안내와 분리, 실행 가이드로 사용하지 않음 |

대시보드의 Documentation 화면은 구조도·파일 구조·DB 스키마 세 문서를 제공합니다.
문서 파일을 이동하거나 이름을 바꾸면 `mentoring/web/app.py`의 허용 목록과
`mentoring/web/templates/index.html`의 문서 버튼도 함께 바꾸고 오프라인 테스트를 실행하세요.

새 다이어그램도 해당 설명 문서 안에 두세요. 같은 내용을 여러 문서에 복제하기보다 링크로 연결합니다.
배포용 이미지가 필요해지면 Mermaid에서 내보낸 결과만 `docs/assets/`에 두고 원문 문서를 명시하세요.
DB 진단 스크립트의 새 출력은 Git에서 제외되는 `runtime/diagnostics/`에 저장됩니다.
