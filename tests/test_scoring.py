import unittest

from codi.analyzer import FileMetrics, FunctionMetrics
from codi.graph import DependencyGraph
from codi.scoring import compute_health, rank_hotspots


def _fn(name: str, complexity: int, length: int = 10, args: int = 2,
        docstring: bool = True) -> FunctionMetrics:
    from codi.complexity import complexity_grade
    return FunctionMetrics(
        name=name, qualname=name, lineno=1, end_lineno=length,
        complexity=complexity, grade=complexity_grade(complexity),
        length=length, args=args, has_docstring=docstring, is_async=False,
    )


class TestScoring(unittest.TestCase):
    def test_clean_code_scores_high(self):
        files = [FileMetrics(path="a.py", loc=50, sloc=40, comment_lines=5,
                             functions=[_fn("f", 2), _fn("g", 3)])]
        health = compute_health(files, DependencyGraph.build(files))
        self.assertGreaterEqual(health.score, 85)
        self.assertIn(health.grade, ("A", "B"))
        self.assertEqual(health.hotspots, [])

    def test_complex_code_scores_lower_and_flags_hotspots(self):
        monster = _fn("monster", complexity=25, length=120, args=8, docstring=False)
        files = [FileMetrics(path="a.py", loc=200, sloc=150, functions=[monster])]
        health = compute_health(files, DependencyGraph.build(files))
        self.assertLess(health.score, 60)
        self.assertEqual(len(health.hotspots), 1)
        self.assertEqual(health.hotspots[0].function.name, "monster")
        reasons = " ".join(health.hotspots[0].reasons)
        self.assertIn("complexity", reasons)
        self.assertIn("parameters", reasons)

    def test_hotspots_ranked_by_risk(self):
        f1 = _fn("mild", complexity=12)
        f2 = _fn("severe", complexity=40, length=200, docstring=False)
        files = [FileMetrics(path="a.py", sloc=100, functions=[f1, f2])]
        spots = rank_hotspots(files)
        self.assertEqual(spots[0].function.name, "severe")

    def test_parse_errors_penalized(self):
        good = [FileMetrics(path="a.py", sloc=10, functions=[_fn("f", 1)])]
        bad = good + [FileMetrics(path="b.py", parse_error="boom")]
        h_good = compute_health(good, DependencyGraph.build(good))
        h_bad = compute_health(bad, DependencyGraph.build(bad))
        self.assertLess(h_bad.score, h_good.score)
        self.assertEqual(h_bad.parse_errors, ["b.py"])

    def test_cycles_penalized(self):
        files = [
            FileMetrics(path="a.py", sloc=10, imports=["b"], functions=[_fn("f", 1)]),
            FileMetrics(path="b.py", sloc=10, imports=["a"], functions=[_fn("g", 1)]),
        ]
        health = compute_health(files, DependencyGraph.build(files))
        self.assertEqual(len(health.cycles), 1)


if __name__ == "__main__":
    unittest.main()
