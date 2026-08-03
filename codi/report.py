"""Self-contained HTML report generation (no external assets)."""

from __future__ import annotations

import datetime
import html
import json

from .analyzer import FileMetrics
from .graph import DependencyGraph
from .scoring import HealthReport

_GRADE_COLORS = {"A": "#22c55e", "B": "#84cc16", "C": "#eab308", "D": "#f97316", "F": "#ef4444"}

_CSS = """
:root { --bg:#0f172a; --card:#1e293b; --text:#e2e8f0; --muted:#94a3b8; --line:#334155; --accent:#38bdf8; }
* { box-sizing:border-box; margin:0; padding:0; }
body { background:var(--bg); color:var(--text); font:15px/1.6 'Segoe UI',system-ui,sans-serif; padding:2rem; }
.wrap { max-width:1080px; margin:0 auto; }
h1 { font-size:1.7rem; margin-bottom:.2rem; }
h2 { font-size:1.15rem; margin:2rem 0 .8rem; color:var(--accent); }
.sub { color:var(--muted); margin-bottom:1.6rem; }
.cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:1rem; }
.card { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:1rem 1.2rem; }
.card .v { font-size:1.6rem; font-weight:700; }
.card .l { color:var(--muted); font-size:.8rem; text-transform:uppercase; letter-spacing:.05em; }
.score { display:flex; align-items:center; gap:1.4rem; background:var(--card); border:1px solid var(--line); border-radius:12px; padding:1.4rem; margin-bottom:1.4rem; }
.ring { width:110px; height:110px; flex-shrink:0; }
table { width:100%; border-collapse:collapse; background:var(--card); border-radius:10px; overflow:hidden; }
th,td { text-align:left; padding:.55rem .9rem; border-bottom:1px solid var(--line); font-size:.88rem; }
th { color:var(--muted); font-size:.75rem; text-transform:uppercase; letter-spacing:.05em; }
tr:last-child td { border-bottom:none; }
.g { display:inline-block; min-width:1.6rem; text-align:center; border-radius:6px; font-weight:700; color:#0f172a; padding:.05rem .3rem; }
.bar { height:8px; border-radius:4px; background:var(--line); overflow:hidden; }
.bar > i { display:block; height:100%; background:var(--accent); }
.muted { color:var(--muted); }
.cycle { background:#7f1d1d33; border:1px solid #ef444455; border-radius:8px; padding:.6rem .9rem; margin-bottom:.5rem; font-family:monospace; font-size:.85rem; }
.ok { color:#22c55e; }
.overflow { overflow-x:auto; }
footer { margin-top:2.5rem; color:var(--muted); font-size:.8rem; }
th.sortable { cursor:pointer; user-select:none; }
th.sortable:hover { color:var(--accent); }
"""

_SORT_JS = """
document.querySelectorAll('table').forEach(table => {
  table.querySelectorAll('th').forEach((th, col) => {
    th.classList.add('sortable');
    let asc = false;
    th.addEventListener('click', () => {
      asc = !asc;
      const rows = [...table.querySelectorAll('tr')].slice(1);
      rows.sort((a, b) => {
        const x = a.cells[col]?.innerText ?? '', y = b.cells[col]?.innerText ?? '';
        const nx = parseFloat(x), ny = parseFloat(y);
        const cmp = (!isNaN(nx) && !isNaN(ny)) ? nx - ny : x.localeCompare(y);
        return asc ? cmp : -cmp;
      });
      rows.forEach(r => table.appendChild(r));
    });
  });
});
"""


def _ring(score: float, grade: str) -> str:
    """SVG donut gauge showing the overall health score."""
    color = _GRADE_COLORS.get(grade, "#94a3b8")
    circumference = 2 * 3.14159 * 45
    filled = circumference * score / 100
    return (
        f'<svg class="ring" viewBox="0 0 110 110">'
        f'<circle cx="55" cy="55" r="45" fill="none" stroke="#334155" stroke-width="10"/>'
        f'<circle cx="55" cy="55" r="45" fill="none" stroke="{color}" stroke-width="10" '
        f'stroke-linecap="round" stroke-dasharray="{filled:.1f} {circumference:.1f}" '
        f'transform="rotate(-90 55 55)"/>'
        f'<text x="55" y="52" text-anchor="middle" fill="{color}" font-size="24" font-weight="700">{grade}</text>'
        f'<text x="55" y="72" text-anchor="middle" fill="#94a3b8" font-size="13">{score:.0f}/100</text>'
        f"</svg>"
    )


def _card(label: str, value: str) -> str:
    """One stat card for the summary grid."""
    return f'<div class="card"><div class="v">{value}</div><div class="l">{label}</div></div>'


def _grade_pill(grade: str) -> str:
    """Colored badge for a complexity grade."""
    return f'<span class="g" style="background:{_GRADE_COLORS.get(grade, "#94a3b8")}">{grade}</span>'


def _hotspot_rows(health: HealthReport) -> str:
    """Table rows for the refactoring-hotspot section."""
    e = html.escape
    return "".join(
        f"<tr><td>{e(h.function.qualname)}</td><td class='muted'>{e(h.file)}:{h.function.lineno}</td>"
        f"<td>{_grade_pill(h.function.grade)}</td><td>{h.function.complexity}</td>"
        f"<td>{h.function.length}</td><td class='muted'>{e('; '.join(h.reasons))}</td></tr>"
        for h in health.hotspots
    ) or "<tr><td colspan='6' class='ok'>No risky functions found — clean codebase.</td></tr>"


def _file_rows(files: list[FileMetrics]) -> str:
    """Table rows for the per-file metrics section."""
    e = html.escape
    max_sloc = max((f.sloc for f in files), default=1) or 1
    return "".join(
        f"<tr><td>{e(f.path)}</td><td>{f.sloc}</td>"
        f"<td><div class='bar'><i style='width:{100 * f.sloc / max_sloc:.0f}%'></i></div></td>"
        f"<td>{len(f.functions)}</td><td>{f.avg_complexity:.1f}</td><td>{f.max_complexity}</td>"
        f"<td>{f.maintainability_index:.0f}</td>"
        f"<td>{f.docstring_coverage:.0%}</td></tr>"
        for f in sorted(files, key=lambda x: x.sloc, reverse=True)
    )


def _dependency_rows(graph: DependencyGraph) -> str:
    """Table rows for the internal-dependencies section."""
    e = html.escape
    fan_in, fan_out = graph.fan_in(), graph.fan_out()
    return "".join(
        f"<tr><td>{e(mod)}</td><td>{fan_in.get(mod, 0)}</td><td>{fan_out.get(mod, 0)}</td>"
        f"<td class='muted'>{e(', '.join(sorted(targets)) or '—')}</td></tr>"
        for mod, targets in sorted(graph.edges.items(), key=lambda kv: -fan_in.get(kv[0], 0))
    )


def _clone_rows(health: HealthReport) -> str:
    """Table rows for the duplicated-functions section."""
    e = html.escape
    return "".join(
        f"<tr><td>{len(g.sites)}</td><td>{g.size}</td>"
        f"<td class='muted'>{e(', '.join(f'{s.file}:{s.lineno} {s.qualname}' for s in g.sites))}</td></tr>"
        for g in health.clone_groups
    ) or "<tr><td colspan='3' class='ok'>✓ No duplicated functions detected.</td></tr>"


def _dead_rows(health: HealthReport) -> str:
    """Table rows for the possibly-dead-code section."""
    e = html.escape
    return "".join(
        f"<tr><td>{e(d.qualname)}</td><td class='muted'>{e(d.file)}:{d.lineno}</td></tr>"
        for d in health.dead_functions
    ) or "<tr><td colspan='2' class='ok'>✓ No unreferenced functions detected.</td></tr>"


def render_html(
    target: str,
    files: list[FileMetrics],
    graph: DependencyGraph,
    health: HealthReport,
) -> str:
    """Render the full analysis as one self-contained HTML page."""
    e = html.escape
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    hotspot_rows = _hotspot_rows(health)
    file_rows = _file_rows(files)
    dep_rows = _dependency_rows(graph)
    clone_rows = _clone_rows(health)
    dead_rows = _dead_rows(health)

    cycles_html = (
        "".join(f"<div class='cycle'>{e(' → '.join(c))}</div>" for c in health.cycles)
        or "<p class='ok'>✓ No circular imports detected.</p>"
    )

    errors_html = (
        "<h2>Parse errors</h2>" + "".join(f"<div class='cycle'>{e(p)}</div>" for p in health.parse_errors)
        if health.parse_errors else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Codi report — {e(target)}</title><style>{_CSS}</style></head>
<body><div class="wrap">
<h1>Codi code-health report</h1>
<div class="sub">{e(target)} · generated {now}</div>

<div class="score">{_ring(health.score, health.grade)}
<div><div style="font-size:1.2rem;font-weight:700">Overall health: {health.score}/100</div>
<div class="muted">Blend of complexity (40), hotspot density (25), documentation (20), import structure (15).</div></div></div>

<div class="cards">
{_card("Files", str(health.total_files))}
{_card("Source lines", f"{health.total_sloc:,}")}
{_card("Functions", str(health.total_functions))}
{_card("Avg complexity", f"{health.avg_complexity:.2f}")}
{_card("Docstring coverage", f"{health.docstring_coverage:.0%}")}
{_card("Import cycles", str(len(health.cycles)))}
{_card("Duplication", f"{health.duplication:.0%}")}
{_card("Dead functions", str(len(health.dead_functions)))}
</div>

<h2>Refactoring hotspots</h2>
<div class="overflow"><table><tr><th>Function</th><th>Location</th><th>Grade</th><th>CC</th><th>Lines</th><th>Why</th></tr>{hotspot_rows}</table></div>

<h2>Files</h2>
<div class="overflow"><table><tr><th>File</th><th>SLOC</th><th></th><th>Funcs</th><th>Avg CC</th><th>Max CC</th><th>MI</th><th>Docs</th></tr>{file_rows}</table></div>

<h2>Internal dependencies</h2>
<div class="overflow"><table><tr><th>Module</th><th>Fan-in</th><th>Fan-out</th><th>Imports</th></tr>{dep_rows}</table></div>

<h2>Duplicated functions</h2>
<div class="overflow"><table><tr><th>Copies</th><th>Statements</th><th>Locations</th></tr>{clone_rows}</table></div>

<h2>Possibly dead code</h2>
<div class="overflow"><table><tr><th>Function</th><th>Location</th></tr>{dead_rows}</table></div>

<h2>Circular imports</h2>
{cycles_html}
{errors_html}

<footer>Generated by <b>Codi</b> — zero-dependency Python code-health analyzer.</footer>
<script>{_SORT_JS}</script>
</div></body></html>"""


def render_json(
    target: str, files: list[FileMetrics], graph: DependencyGraph, health: HealthReport
) -> str:
    """Machine-readable summary of the same analysis."""
    return json.dumps(
        {
            "target": target,
            "health": {
                "score": health.score,
                "grade": health.grade,
                "files": health.total_files,
                "sloc": health.total_sloc,
                "functions": health.total_functions,
                "avg_complexity": health.avg_complexity,
                "docstring_coverage": health.docstring_coverage,
                "cycles": health.cycles,
                "parse_errors": health.parse_errors,
                "duplication": health.duplication,
            },
            "clones": [
                {
                    "copies": len(g.sites),
                    "statements": g.size,
                    "sites": [
                        {"file": s.file, "function": s.qualname, "line": s.lineno}
                        for s in g.sites
                    ],
                }
                for g in health.clone_groups
            ],
            "dead_functions": [
                {"file": d.file, "function": d.qualname, "line": d.lineno}
                for d in health.dead_functions
            ],
            "hotspots": [
                {
                    "file": h.file,
                    "function": h.function.qualname,
                    "line": h.function.lineno,
                    "complexity": h.function.complexity,
                    "grade": h.function.grade,
                    "risk": h.risk,
                    "reasons": h.reasons,
                }
                for h in health.hotspots
            ],
            "files": [
                {
                    "path": f.path,
                    "sloc": f.sloc,
                    "functions": len(f.functions),
                    "avg_complexity": round(f.avg_complexity, 2),
                    "maintainability_index": round(f.maintainability_index, 1),
                }
                for f in files
            ],
        },
        indent=2,
    )
