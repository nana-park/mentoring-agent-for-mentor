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
    html = env.get_template('index.html').render()
    html = html.replace('/static/', './pages-assets/')
    html = html.replace('<title>Mentoring CRM Dashboard</title>', '<title>Mentoring CRM · 화면 데모</title>')
    html = html.replace('<head>', '''<head>
    <meta http-equiv="Content-Security-Policy" content="connect-src 'none'; form-action 'none'; object-src 'none'; base-uri 'self'">
    <meta name="referrer" content="no-referrer">
    <script src="./pages-assets/docs-data.js"></script>
    <script src="./pages-assets/demo.js"></script>''', 1)
    html = html.replace('<body>', '''<body>
    <aside id="pages-demo-banner" role="note" style="position:relative;z-index:100;padding:14px 24px;background:#fff1c2;color:#382900;text-align:center;font:14px/1.6 sans-serif">
        <strong>화면 체험용 데모</strong> · AI / Gmail / Notion 연동 없음<br>
        입력은 이 탭에만 임시 보관되며 새로고침하면 초기화됩니다. 실제 학생·업무·인증 정보는 입력하지 마세요.
        실행 버튼은 입력 내용과 무관한 가상 예시를 보여줍니다.
    </aside>''', 1)
    start = html.index('            <div class="context-notice">')
    end = html.index('            <label class="context-check">', start)
    html = html[:start] + '''            <div class="context-notice">
                <strong>GitHub Pages 화면 데모</strong>
                <p>이 화면의 입력·저장은 현재 탭의 메모리에서만 동작합니다. 새로고침하면 모두 초기화됩니다.
                AI 분석·ChatGPT 기록 연동·파일 저장·Notion 전송은 실행하지 않습니다. 가상의 정보로 체험해주세요.</p>
            </div>
''' + html[end:]
    for old, new in {
        '위 전송 범위를 확인했고, 저장한 업무 맥락을 분석에 사용합니다': '데모 미리보기에 선택한 업무 맥락을 포함합니다 (전송 없음)',
        '로컬 맥락 삭제': '임시 맥락 삭제',
        '다음 분석에 전달할 저장본 미리보기': '이 탭의 임시 저장본 미리보기 (전송 없음)',
        '실제 서비스명과 사용자·AI 기능·단계·문제·제약을 적어야 구체적으로 제안할 수 있어요.': '데모에서는 가상의 서비스명과 사용자·AI 기능·문제를 적어주세요.',
        'Scheduled Automation': 'Scheduled Automation · 데모에서는 실행되지 않음',
        'Scans Gmail and processes newly received Google Meet meeting notes.': '메일 자동 수집 화면을 체험합니다. 실제 Gmail은 조회하지 않습니다.',
        'Batch processes text files saved in the local folder.': '일괄 처리 예시를 봅니다. PC의 파일은 읽지 않습니다.',
        'Paste text directly to instantly call Gemini and save to DB without creating local files.': '가상의 텍스트로 입력 흐름을 체험합니다. AI 호출·DB 저장 없이 고정 예시를 표시합니다.',
        'Collect mentor insights to generate practical planning retrospectives.': '멘토 업무 적용 가설과 작은 실험의 고정 예시를 봅니다. 실제 회고록은 생성하지 않습니다.',
        'System architecture and database schema guides.': '아래 문서·다이어그램은 실제 로컬 앱의 구조입니다. 공개 데모는 외부 서비스에 연결하지 않습니다.',
        'id="auto-toggle"': 'id="auto-toggle" disabled title="예약 실행은 로컬 앱에서 사용할 수 있습니다"',
        '모든 작업이 완료': '데모 체험이 완료',
    }.items():
        html = html.replace(old, new)
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
                      '이 탭에 임시 저장한 데모 맥락을 삭제할까요?').replace(
                '로컬 업무 맥락을 삭제했습니다.', '이 탭의 임시 맥락을 삭제했습니다.').encode('utf-8')
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
