"""Tests for cognitive complexity, Halstead, type-hint coverage, config, GHA."""

import ast
import tempfile
import unittest
from pathlib import Path

from codi.analyzer import analyze_file
from codi.cognitive import cognitive_complexity, halstead_volume, maintainability_index
from codi.config import load_config
from codi.gha import emit_annotations
from codi.scoring import HealthReport, Hotspot
from codi.analyzer import FunctionMetrics


def _parse_fn(src):
    return ast.parse(src).body[0]


class TestCognitive(unittest.TestCase):
    def test_flat_function_is_zero(self):
        self.assertEqual(cognitive_complexity(_parse_fn("def f():\n return 1")), 0)

    def test_nesting_costs_more(self):
        flat = _parse_fn("def f(x):\n if x: pass\n if x: pass")
        nested = _parse_fn("def f(x):\n if x:\n  if x: pass")
        # two sibling ifs: 1+1=2; nested if-in-if: 1 + (1+1)=3
        self.assertEqual(cognitive_complexity(flat), 2)
        self.assertEqual(cognitive_complexity(nested), 3)

    def test_else_adds_one(self):
        fn = _parse_fn("def f(x):\n if x: pass\n else: pass")
        self.assertEqual(cognitive_complexity(fn), 2)

    def test_bool_op(self):
        fn = _parse_fn("def f(a, b):\n return a and b")
        self.assertEqual(cognitive_complexity(fn), 1)


class TestHalstead(unittest.TestCase):
    def test_empty_is_zero(self):
        self.assertEqual(halstead_volume(ast.parse("")), 0.0)

    def test_volume_grows_with_code(self):
        small = halstead_volume(ast.parse("x = 1"))
        big = halstead_volume(ast.parse("x = 1\ny = x + 2\nz = y * x - 3"))
        self.assertGreater(big, small)

    def test_mi_bounds(self):
        self.assertEqual(maintainability_index(0, 0, 0), 100.0)
        self.assertLessEqual(maintainability_index(50000, 30, 2000), 100.0)
        self.assertGreaterEqual(maintainability_index(50000, 30, 2000), 0.0)


class TestAnnotations(unittest.TestCase):
    def _analyze(self, src):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "m.py"
            p.write_text(src, encoding="utf-8")
            return analyze_file(p)

    def test_fully_annotated(self):
        fm = self._analyze("def f(x: int) -> int:\n    return x\n")
        self.assertTrue(fm.functions[0].is_annotated)
        self.assertEqual(fm.annotation_coverage, 1.0)

    def test_missing_return_annotation(self):
        fm = self._analyze("def f(x: int):\n    return x\n")
        self.assertFalse(fm.functions[0].is_annotated)

    def test_self_is_exempt(self):
        fm = self._analyze("class C:\n    def m(self, x: int) -> None:\n        pass\n")
        self.assertTrue(fm.functions[0].is_annotated)


class TestConfig(unittest.TestCase):
    def test_codi_toml(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "codi.toml").write_text(
                'fail_under = 75\nmin_clone_size = 6\n', encoding="utf-8")
            cfg = load_config(root)
            if cfg:  # tomllib present (3.11+)
                self.assertEqual(cfg["fail_under"], 75)
                self.assertEqual(cfg["min_clone_size"], 6)

    def test_missing_config_is_empty(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(load_config(Path(td)), {})


class TestGha(unittest.TestCase):
    def test_hotspot_annotation_format(self):
        fn = FunctionMetrics(name="f", qualname="f", lineno=3, end_lineno=9,
                             complexity=12, grade="C", length=7, args=1,
                             has_docstring=False, is_async=False)
        health = HealthReport(
            score=50, grade="D", total_files=1, total_loc=10, total_sloc=8,
            total_functions=1, avg_complexity=12, docstring_coverage=0,
            comment_ratio=0, cycles=[["a", "b", "a"]], parse_errors=[],
            hotspots=[Hotspot(file="m.py", function=fn, risk=30,
                              reasons=["complexity 12"], advice="split it")])
        lines = emit_annotations(health)
        self.assertTrue(lines[0].startswith("::warning file=m.py,line=3,"))
        self.assertIn("try: split it", lines[0])
        self.assertIn("Codi import cycle", lines[-1])


if __name__ == "__main__":
    unittest.main()
