"""Command-line interface for Codi."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .analyzer import analyze_project
from .graph import DependencyGraph
from .report import render_html, render_json
from .scoring import compute_health

_GRADE_ICON = {"A": "🟢", "B": "🟢", "C": "🟡", "D": "🟠", "F": "🔴"}


def _print_summary(target: str, health, files) -> None:
    """Render the terminal health summary with hotspots and cycles."""
    bar_len = 30
    filled = int(bar_len * health.score / 100)
    bar = "█" * filled + "░" * (bar_len - filled)
    print()
    print(f"  Codi v{__version__} — {target}")
    print(f"  {'─' * 60}")
    print(f"  Health  {bar}  {health.score}/100  grade {health.grade}")
    print(f"  Files: {health.total_files}   SLOC: {health.total_sloc:,}   "
          f"Functions: {health.total_functions}   Avg CC: {health.avg_complexity}")
    print(f"  Docstrings: {health.docstring_coverage:.0%}   "
          f"Import cycles: {len(health.cycles)}   Parse errors: {len(health.parse_errors)}")
    if health.hotspots:
        print(f"\n  Top refactoring hotspots:")
        for h in health.hotspots[:5]:
            icon = _GRADE_ICON.get(h.function.grade, "⚪")
            print(f"   {icon} {h.function.qualname}  ({h.file}:{h.function.lineno})  "
                  f"CC={h.function.complexity}  — {'; '.join(h.reasons)}")
    for cycle in health.cycles:
        print(f"\n  ⚠ circular import: {' → '.join(cycle)}")
    print()


def main(argv: list[str] | None = None) -> int:
    """Entry point: parse args, analyze, emit reports, apply CI gate."""
    # Legacy Windows consoles default to cp1252; keep unicode output safe.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(
        prog="codi",
        description="Zero-dependency Python code-health analyzer: "
        "complexity, hotspots, dependency graph, HTML report.",
    )
    parser.add_argument("path", nargs="?", default=".", help="file or directory to analyze")
    parser.add_argument("--html", metavar="FILE", help="write a self-contained HTML report")
    parser.add_argument("--json", metavar="FILE", help="write a JSON report ('-' for stdout)")
    parser.add_argument("--fail-under", type=float, metavar="SCORE",
                        help="exit non-zero if health score is below SCORE (for CI gates)")
    parser.add_argument("--version", action="version", version=f"codi {__version__}")
    args = parser.parse_args(argv)

    root = Path(args.path).resolve()
    if not root.exists():
        parser.error(f"path does not exist: {root}")

    files = analyze_project(root)
    if not files:
        print(f"No Python files found under {root}", file=sys.stderr)
        return 1

    graph = DependencyGraph.build(files)
    health = compute_health(files, graph)
    target = str(root)

    if args.html:
        Path(args.html).write_text(
            render_html(target, files, graph, health), encoding="utf-8"
        )
        print(f"HTML report written to {args.html}")
    if args.json == "-":
        print(render_json(target, files, graph, health))
    elif args.json:
        Path(args.json).write_text(
            render_json(target, files, graph, health), encoding="utf-8"
        )
        print(f"JSON report written to {args.json}")

    if args.json != "-":
        _print_summary(target, health, files)

    if args.fail_under is not None and health.score < args.fail_under:
        print(f"FAIL: health score {health.score} is below threshold {args.fail_under}",
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
