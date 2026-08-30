"""Check the public export boundary without loading the Flask app or private data."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_pages', ROOT / 'scripts/build_pages.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class PagesExportTests(unittest.TestCase):
    def test_export_is_allowlisted_and_works_under_project_subpath(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            builder.build(output)
            names = {p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()}
            self.assertEqual(names, {'index.html', '.nojekyll', 'pages-assets/demo.js', 'pages-assets/docs-data.js',
                                    *(f'pages-assets/{name}' for name in builder.ASSETS)})
            html = (output / 'index.html').read_text(encoding='utf-8')
            self.assertNotIn('/static/', html)
            self.assertNotIn('{%', html)
            self.assertIn("connect-src 'none'", html)
            self.assertIn('pages-demo-banner', html)
            self.assertNotIn('저장은 이 PC의 로컬 파일에만 합니다', html)
            self.assertLess(html.index('pages-assets/demo.js'), html.index('fetch('))
            self.assertIn('id="auto-toggle" disabled', html)
            # Same sources must generate byte-identical checked-in artifacts.
            for name in names:
                self.assertEqual((output / name).read_bytes(), (ROOT / name).read_bytes(), name)


if __name__ == '__main__':
    unittest.main()
