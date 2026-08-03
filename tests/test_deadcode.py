import tempfile
import unittest
from pathlib import Path

from codi.analyzer import analyze_file
from codi.deadcode import find_dead_functions


class TestDeadCode(unittest.TestCase):
    def _analyze(self, mapping):
        self.tmp = tempfile.TemporaryDirectory()
        files, sources = [], {}
        for name, src in mapping.items():
            p = Path(self.tmp.name) / name
            p.write_text(src, encoding="utf-8")
            files.append(analyze_file(p, display_path=name))
            sources[name] = src
        self.addCleanup(self.tmp.cleanup)
        return files, sources

    def test_unreferenced_function_flagged(self):
        files, sources = self._analyze({
            "mod.py": "def used():\n    return 1\n\ndef orphan():\n    return 2\n",
            "app.py": "from mod import used\nprint(used())\n",
        })
        dead = find_dead_functions(files, sources)
        self.assertEqual([d.qualname for d in dead], ["orphan"])

    def test_cross_file_reference_counts(self):
        files, sources = self._analyze({
            "mod.py": "def helper():\n    return 1\n",
            "app.py": "import mod\nprint(mod.helper())\n",
        })
        self.assertEqual(find_dead_functions(files, sources), [])

    def test_all_export_counts_as_reference(self):
        files, sources = self._analyze({
            "mod.py": '__all__ = ["api"]\n\ndef api():\n    return 1\n',
        })
        self.assertEqual(find_dead_functions(files, sources), [])

    def test_exempt_names_not_flagged(self):
        files, sources = self._analyze({
            "mod.py": (
                "def main():\n    return 1\n\n"
                "def test_something():\n    return 2\n\n"
                "def __repr__():\n    return 'x'\n"
            ),
        })
        self.assertEqual(find_dead_functions(files, sources), [])

    def test_decorator_reference_counts(self):
        files, sources = self._analyze({
            "mod.py": (
                "def deco(f):\n    return f\n\n"
                "@deco\ndef target():\n    return 1\n\n"
                "print(target())\n"
            ),
        })
        self.assertEqual(find_dead_functions(files, sources), [])


if __name__ == "__main__":
    unittest.main()
