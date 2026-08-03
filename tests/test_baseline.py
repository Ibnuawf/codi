import tempfile
import unittest
from pathlib import Path

from codi.analyzer import FileMetrics, FunctionMetrics
from codi.baseline import compare, save_baseline, snapshot
from codi.complexity import complexity_grade
from codi.graph import DependencyGraph
from codi.scoring import compute_health


def _health(complexity: int):
    fn = FunctionMetrics(
        name="f", qualname="f", lineno=1, end_lineno=10,
        complexity=complexity, grade=complexity_grade(complexity),
        length=10, args=1, has_docstring=True, is_async=False,
    )
    files = [FileMetrics(path="a.py", loc=20, sloc=15, functions=[fn])]
    return compute_health(files, DependencyGraph.build(files))


class TestBaseline(unittest.TestCase):
    def test_snapshot_round_trip(self):
        health = _health(2)
        snap = snapshot(health, extra={"clone_groups": 0})
        self.assertEqual(snap["grade"], health.grade)
        self.assertEqual(snap["clone_groups"], 0)

    def test_save_and_compare_detects_regression(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "baseline.json"
            save_baseline(path, _health(2))
            deltas = compare(path, _health(20))
            metrics = {d.metric: d for d in deltas}
            self.assertIn("score", metrics)
            self.assertFalse(metrics["score"].improved)
            self.assertIn("avg_complexity", metrics)
            self.assertFalse(metrics["avg_complexity"].improved)

    def test_identical_runs_produce_no_deltas(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "baseline.json"
            save_baseline(path, _health(3))
            self.assertEqual(compare(path, _health(3)), [])

    def test_improvement_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "baseline.json"
            save_baseline(path, _health(20))
            deltas = compare(path, _health(2))
            score = next(d for d in deltas if d.metric == "score")
            self.assertTrue(score.improved)


if __name__ == "__main__":
    unittest.main()
