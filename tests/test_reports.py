"""Tests for markdown/badge/viz/history/churn additions (v3)."""

import json
import tempfile
import unittest
from pathlib import Path

from codi.analyzer import FileMetrics, FunctionMetrics
from codi.churn import ChurnInfo, churn_risk
from codi.graph import DependencyGraph
from codi.history import append_history, load_history, sparkline
from codi.markdown import render_badge, render_markdown
from codi.scoring import HealthReport
from codi.viz import dependency_svg, treemap_svg, trend_svg


def _fn(name="f", cc=3, length=10):
    return FunctionMetrics(name=name, qualname=name, lineno=1, end_lineno=length,
                           complexity=cc, grade="A", length=length, args=1,
                           has_docstring=True, is_async=False)


def _health(score=88.0):
    return HealthReport(score=score, grade="B", total_files=2, total_loc=100,
                        total_sloc=80, total_functions=4, avg_complexity=2.5,
                        docstring_coverage=0.75, comment_ratio=0.1,
                        hotspots=[], cycles=[], parse_errors=[])


class TestMarkdown(unittest.TestCase):
    def test_contains_score_and_metrics(self):
        md = render_markdown("proj", _health())
        self.assertIn("88.0/100", md)
        self.assertIn("| Files | 2 |", md)

    def test_churn_section(self):
        md = render_markdown("proj", _health(), [("a.py", 10, 4.0, 40.0)])
        self.assertIn("Churn risk", md)
        self.assertIn("| a.py | 10 | 4.0 | 40.0 |", md)


class TestBadge(unittest.TestCase):
    def test_badge_is_svg_with_score(self):
        svg = render_badge(_health())
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn("88/100", svg)


class TestViz(unittest.TestCase):
    def test_dependency_svg(self):
        g = DependencyGraph(edges={"a": {"b"}, "b": set()})
        svg = dependency_svg(g, cycles=[])
        self.assertIn("<svg", svg)
        self.assertIn("<circle", svg)

    def test_treemap(self):
        files = [FileMetrics(path="a.py", sloc=50, functions=[_fn()]),
                 FileMetrics(path="b.py", sloc=30)]
        svg = treemap_svg(files)
        self.assertIn("<rect", svg)
        self.assertIn("a.py", svg)

    def test_trend_needs_two_points(self):
        self.assertEqual(trend_svg([{"score": 80}]), "")
        self.assertIn("polyline", trend_svg([{"score": 80}, {"score": 90}]))


class TestHistory(unittest.TestCase):
    def test_append_and_load(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "hist.json"
            append_history(p, _health(80.0))
            entries = append_history(p, _health(90.0))
            self.assertEqual(len(entries), 2)
            self.assertEqual(load_history(p)[1]["score"], 90.0)

    def test_load_missing_or_corrupt(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "nope.json"
            self.assertEqual(load_history(p), [])
            p.write_text("{not json", encoding="utf-8")
            self.assertEqual(load_history(p), [])

    def test_sparkline(self):
        self.assertEqual(len(sparkline([0, 50, 100])), 3)
        self.assertEqual(sparkline([]), "")


class TestChurnRisk(unittest.TestCase):
    def test_ranked_by_risk(self):
        churn = {"a.py": ChurnInfo("a.py", 10, 2), "b.py": ChurnInfo("b.py", 2, 1)}
        ranked = churn_risk(churn, {"a.py": 3.0, "b.py": 8.0})
        self.assertEqual(ranked[0][0], "a.py")
        self.assertEqual(ranked[0][3], 30.0)

    def test_skips_files_without_complexity(self):
        ranked = churn_risk({"x.py": ChurnInfo("x.py", 5, 1)}, {})
        self.assertEqual(ranked, [])


if __name__ == "__main__":
    unittest.main()
