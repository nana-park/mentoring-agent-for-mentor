"""Export only allowlisted public UI assets. Never imports the app or loads secrets.

Run after UI/docs changes: python scripts/build_pages.py
Commit index.html, .nojekyll and pages-assets/ with the source changes.
"""
import argparse
import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]
DOCS = ('architecture_diagram.md', 'database_schema.md', 'project_structure.md', 'mentor_insights.md')
ASSETS = ('mentor_context.css', 'mentor_context.js', 'images/breadme_logo.svg', 'images/file_explorer.svg')


def build(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    assets = output / 'pages-assets'
    assets.mkdir(exist_ok=True)
    env = Environment(loader=FileSystemLoader(ROOT / 'mentoring/web/templates'), autoescape=select_autoescape())
    html = env.get_template('index.html').render(pages_demo=True)
    html = html.replace('/static/', './pages-assets/')
    html = html.replace('<title>Mentoring CRM Dashboard</title>', '<title>Mentoring CRM</title>')
    html = html.replace('<head>', '''<head>
    <meta http-equiv="Content-Security-Policy" content="connect-src 'none'; form-action 'none'; object-src 'none'; base-uri 'self'">
    <meta name="referrer" content="no-referrer">
    <script src="./pages-assets/docs-data.js"></script>
    <script src="./pages-assets/demo.js"></script>''', 1)
    # Keep navigation and connection status in separate normal-flow rows.
    html = html.replace('</head>', '''<style>
        .top-nav { position:relative; inset:auto; flex-wrap:wrap; gap:16px;
            background:#111; border-bottom:1px solid #292929; padding:20px 30px; }
        .top-nav .top-link { color:#f5f5f5; }
        #pages-demo-banner { padding:12px 24px; background:#191919; color:#c9c9c9;
            text-align:center; font:13px/1.7 sans-serif; border-bottom:1px solid #292929; }
        #pages-demo-banner strong { color:#f1c777; }
        @media(max-width:480px) {
            .top-nav { padding:16px; gap:12px; }
            .nav-left { gap:16px; }
            .profile-pic { height:20px; }
            #pages-demo-banner { padding:12px 16px; text-align:left; }
        }
    </style></head>''', 1)
    html = html.replace('<body>', '''<body>
    <aside id="pages-demo-banner" role="note">
        <strong>외부 서비스 미연결</strong> · AI / Gmail / Notion 연결 전입니다.<br>
        현재 실행 버튼은 가상 예시를 표시하고, 입력은 새로고침하면 초기화됩니다. 실제 학생·업무·API 정보는 입력하지 마세요.
    </aside>''', 1)
    start = html.index('            <div class="context-notice">')
    end = html.index('            <label class="context-check">', start)
    html = html[:start] + '''            <div class="context-notice">
                <strong>업무 맥락 저장 안내</strong>
                <p>이 화면의 입력·저장은 현재 탭의 메모리에서만 동작합니다. 새로고침하면 모두 초기화됩니다.
                AI 분석·ChatGPT 기록 연동·파일 저장·Notion 전송은 실행하지 않습니다. 민감한 정보는 입력하지 마세요.</p>
            </div>
''' + html[end:]
    for old, new in {
        '위 전송 범위를 확인했고, 저장한 업무 맥락을 분석에 사용합니다': '검토한 서비스·메모를 아래 요약에 표시',
        '로컬 맥락 삭제': '입력 내용 지우기',
        '저장본 다시 불러오기': '마지막 저장 상태로 되돌리기',
        '다음 분석에 전달할 저장본 미리보기': '선택한 내용 확인',
        '실제 서비스명과 사용자·AI 기능·단계·문제·제약을 적어야 구체적으로 제안할 수 있어요.': '서비스명과 사용자·AI 기능·해결할 문제를 정리하세요. 민감한 정보는 제외해주세요.',
        'Scans Gmail and processes newly received Google Meet meeting notes.': 'Gmail의 멘토링 메일과 Google Meet 회의록 자동 수집',
        'Batch processes text files saved in the local folder.': '폴더에 모아둔 회의록 텍스트 파일 일괄 처리',
        'Paste text directly to instantly call Gemini and save to DB without creating local files.': '회의록을 직접 입력하고 학생별 내용을 검토하는 작업 공간',
        'Collect mentor insights to generate practical planning retrospectives.': '멘토링에서 발견한 인사이트와 서비스 적용 아이디어 정리',
        'System architecture and database schema guides.': '아래 문서·다이어그램은 실제 로컬 앱의 구조입니다. 현재 공개 화면은 외부 서비스에 연결하지 않습니다.',
        'Extracts student count and names<br>to prevent incorrect or duplicate database entries.': '가상의 학생 예시를 표시합니다.<br>입력 내용을 AI로 분석하지 않습니다.',
        'Review the extracted information<br>and permanently save to the database.': '학생별 내용을 검토합니다.<br>외부 서비스 연결 전에는 예시 결과만 표시합니다.',
        'Execute & Save to Notion (Step 2)': '결과 보기',
        'Analyze Students (Step 1)': '학생 예시 보기 (분석 없음)',
        'Direct Entry Successful': '입력 예시 확인 완료',
        '${type} successful': '${type} 예시 확인 완료',
        'Saved!': '이 탭에 임시 저장됨',
        '모든 작업이 완료': '예시 확인이 완료',
    }.items():
        html = html.replace(old, new)
    html = html.replace('<div class="context-actions">', '<p class="context-selection-help">각 서비스·메모의 검토 완료 항목만 표시합니다. 체크 후 아래 ‘맥락 저장’을 누르세요. 현재 웹에서는 AI에 보내지 않습니다.</p><div class="context-actions">')
    html = '\n'.join(line.rstrip() for line in html.splitlines()) + '\n'
    (output / 'index.html').write_text(html, encoding='utf-8')
    (output / '.nojekyll').write_text('', encoding='utf-8')
    for name in ASSETS:
        content = (ROOT / 'mentoring/web/static' / name).read_bytes()
        if name == 'mentor_context.js':
            content = content.decode('utf-8').replace(
                '로컬에 저장했습니다. 다음 분석부터 저장한 사용 설정이 적용됩니다.',
                '이 탭에 임시 저장했습니다. 새로고침하면 초기화되며 AI는 호출하지 않습니다.'
            ).replace('이 PC에 저장한 업무 맥락 전체를 삭제할까요? 이미 Notion에 저장한 인사이트는 남습니다.',
                      '이 탭에 임시 저장한 맥락을 삭제할까요?').replace(
                '로컬 업무 맥락을 삭제했습니다.', '입력 내용을 지웠습니다.').replace(
                '사용 꺼짐 — 업무 맥락을 전달하지 않음', '표시가 꺼져 있습니다. 위 항목을 체크하고 ‘맥락 저장’을 누르면 선택한 내용을 확인할 수 있습니다.').encode('utf-8')
        destination = assets / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    (assets / 'demo.js').write_bytes((ROOT / 'scripts/pages_demo.js').read_bytes())
    docs = {name: (ROOT / 'docs' / name).read_text(encoding='utf-8') for name in DOCS}
    (assets / 'docs-data.js').write_text('window.MENTORING_DEMO_DOCS = ' + json.dumps(docs, ensure_ascii=False) + ';\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT)
    build(parser.parse_args().output.resolve())
