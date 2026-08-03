"""Project-level health scoring and hotspot ranking."""

from __future__ import annotations

from dataclasses import dataclass

from .analyzer import FileMetrics, FunctionMetrics
from .graph import DependencyGraph


@dataclass
class Hotspot:
    """A function that most needs attention, with the reasons why."""

    file: str
    function: FunctionMetrics
    risk: float
    reasons: list[str]


@dataclass
class HealthReport:
    score: float          # 0-100
    grade: str            # A-F
    total_files: int
    total_loc: int
    total_sloc: int
    total_functions: int
    avg_complexity: float
    docstring_coverage: float
    comment_ratio: float
    hotspots: list[Hotspot]
    cycles: list[list[str]]
    parse_errors: list[str]


def _grade(score: float) -> str:
    """Letter grade for a 0-100 health score."""
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def rank_hotspots(files: list[FileMetrics], limit: int = 15) -> list[Hotspot]:
    """Rank functions by a blended risk of complexity, length and args."""
    spots: list[Hotspot] = []
    for f in files:
        for fn in f.functions:
            reasons = []
            if fn.complexity > 10:
                reasons.append(f"complexity {fn.complexity} (grade {fn.grade})")
            if fn.length > 60:
                reasons.append(f"{fn.length} lines long")
            if fn.args > 5:
                reasons.append(f"{fn.args} parameters")
            if not fn.has_docstring and fn.complexity > 5:
                reasons.append("complex but undocumented")
            if not reasons:
                continue
            risk = (
                fn.complexity * 2.0
                + fn.length / 15.0
                + max(0, fn.args - 5) * 3.0
                + (3.0 if not fn.has_docstring else 0.0)
            )
            spots.append(Hotspot(file=f.path, function=fn, risk=round(risk, 1), reasons=reasons))
    spots.sort(key=lambda s: s.risk, reverse=True)
    return spots[:limit]


def compute_health(files: list[FileMetrics], graph: DependencyGraph) -> HealthReport:
    """Blend complexity, documentation, structure and errors into one score."""
    parsed = [f for f in files if f.parse_error is None]
    all_functions = [fn for f in parsed for fn in f.functions]
    total_sloc = sum(f.sloc for f in files)
    total_comments = sum(f.comment_lines for f in files)

    avg_cx = (
        sum(fn.complexity for fn in all_functions) / len(all_functions)
        if all_functions else 1.0
    )
    doc_cov = (
        sum(fn.has_docstring for fn in all_functions) / len(all_functions)
        if all_functions else 1.0
    )
    comment_ratio = total_comments / max(total_sloc, 1)
    cycles = graph.find_cycles()
    worst_share = (
        sum(fn.complexity > 10 for fn in all_functions) / len(all_functions)
        if all_functions else 0.0
    )

    # Score components (sum of maximums = 100)
    complexity_score = max(0.0, 40.0 - (avg_cx - 1.0) * 6.0)      # 40 pts
    hotspot_score = max(0.0, 25.0 * (1.0 - worst_share * 4.0))    # 25 pts
    doc_score = 20.0 * doc_cov                                     # 20 pts
    structure_score = max(0.0, 15.0 - 5.0 * len(cycles))           # 15 pts
    penalty = 5.0 * sum(f.parse_error is not None for f in files)

    score = max(0.0, min(100.0, complexity_score + hotspot_score + doc_score + structure_score - penalty))

    return HealthReport(
        score=round(score, 1),
        grade=_grade(score),
        total_files=len(files),
        total_loc=sum(f.loc for f in files),
        total_sloc=total_sloc,
        total_functions=len(all_functions),
        avg_complexity=round(avg_cx, 2),
        docstring_coverage=round(doc_cov, 3),
        comment_ratio=round(comment_ratio, 3),
        hotspots=rank_hotspots(parsed),
        cycles=cycles,
        parse_errors=[f.path for f in files if f.parse_error is not None],
    )
