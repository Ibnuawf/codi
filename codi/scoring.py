"""Project-level health scoring and hotspot ranking."""

from __future__ import annotations

from dataclasses import dataclass, field

from .analyzer import FileMetrics, FunctionMetrics
from .deadcode import DeadFunction
from .duplication import CloneGroup, duplication_ratio
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
    clone_groups: list[CloneGroup] = field(default_factory=list)
    dead_functions: list[DeadFunction] = field(default_factory=list)
    duplication: float = 0.0


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


def _function_ratio(functions: list[FunctionMetrics], predicate, default: float) -> float:
    """Share of functions matching predicate, or default when there are none."""
    if not functions:
        return default
    return sum(1 for fn in functions if predicate(fn)) / len(functions)


def _blend_score(avg_cx: float, worst_share: float, doc_cov: float,
                 cycle_count: int, dup: float, dead_share: float,
                 error_count: int) -> float:
    """Weighted 0-100 blend of all quality components.

    Weights (max 100): complexity 35, hotspot density 20, documentation 15,
    import structure 10, duplication 10, dead code 10, minus 5 per
    unparseable file.
    """
    components = (
        max(0.0, 35.0 - (avg_cx - 1.0) * 5.5),
        max(0.0, 20.0 * (1.0 - worst_share * 4.0)),
        15.0 * doc_cov,
        max(0.0, 10.0 - 4.0 * cycle_count),
        max(0.0, 10.0 * (1.0 - dup * 5.0)),
        max(0.0, 10.0 * (1.0 - dead_share * 5.0)),
    )
    return max(0.0, min(100.0, sum(components) - 5.0 * error_count))


def compute_health(
    files: list[FileMetrics],
    graph: DependencyGraph,
    clones: list[CloneGroup] | None = None,
    dead: list[DeadFunction] | None = None,
) -> HealthReport:
    """Blend complexity, docs, structure, duplication and dead code into one score."""
    clones = clones or []
    dead = dead or []
    parsed = [f for f in files if f.parse_error is None]
    all_functions = [fn for f in parsed for fn in f.functions]
    total_sloc = sum(f.sloc for f in files)

    avg_cx = (
        sum(fn.complexity for fn in all_functions) / len(all_functions)
        if all_functions else 1.0
    )
    doc_cov = _function_ratio(all_functions, lambda fn: fn.has_docstring, 1.0)
    worst_share = _function_ratio(all_functions, lambda fn: fn.complexity > 10, 0.0)
    comment_ratio = sum(f.comment_lines for f in files) / max(total_sloc, 1)
    cycles = graph.find_cycles()
    dup = duplication_ratio(clones, len(all_functions))
    dead_share = len(dead) / max(len(all_functions), 1)
    error_count = sum(f.parse_error is not None for f in files)

    score = _blend_score(avg_cx, worst_share, doc_cov, len(cycles),
                         dup, dead_share, error_count)

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
        clone_groups=clones,
        dead_functions=dead,
        duplication=round(dup, 3),
    )
