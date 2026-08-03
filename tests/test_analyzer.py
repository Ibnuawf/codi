import tempfile
import unittest
from pathlib import Path

from codi.analyzer import analyze_file, analyze_project, discover_python_files


SAMPLE = '''"""Module docstring."""
import os
from json import dumps


class Greeter:
    """A class."""

    def greet(self, name):
        """Say hello."""
        if name:
            return f"hello {name}"
        return "hello"


async def fetch(url, retries=3):
    for i in range(retries):
        if i:
            pass
    return url
'''


class TestAnalyzer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, rel: str, content: str) -> Path:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def test_analyze_file_metrics(self):
        path = self._write("sample.py", SAMPLE)
        m = analyze_file(path)
        self.assertIsNone(m.parse_error)
        self.assertEqual(m.classes, 1)
        self.assertIn("os", m.imports)
        self.assertIn("json", m.imports)
        names = {f.qualname for f in m.functions}
        self.assertEqual(names, {"Greeter.greet", "fetch"})
        greet = next(f for f in m.functions if f.name == "greet")
        self.assertTrue(greet.has_docstring)
        self.assertEqual(greet.complexity, 2)
        fetch = next(f for f in m.functions if f.name == "fetch")
        self.assertTrue(fetch.is_async)
        self.assertFalse(fetch.has_docstring)

    def test_syntax_error_is_captured(self):
        path = self._write("bad.py", "def broken(:\n")
        m = analyze_file(path)
        self.assertIsNotNone(m.parse_error)

    def test_discover_skips_venv_and_pycache(self):
        self._write("app.py", "x = 1\n")
        self._write(".venv/lib/junk.py", "x = 1\n")
        self._write("__pycache__/cached.py", "x = 1\n")
        found = discover_python_files(self.root)
        self.assertEqual([p.name for p in found], ["app.py"])

    def test_analyze_project_relative_paths(self):
        self._write("pkg/mod.py", "def f():\n    return 1\n")
        results = analyze_project(self.root)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].path, "pkg/mod.py")


if __name__ == "__main__":
    unittest.main()
