# Codi 🩺

**Zero-dependency Python code-health analyzer.** One command gives you cyclomatic
complexity per function, refactoring hotspots ranked by risk, **git churn × complexity
risk** (the files most likely to break next), **clone detection** (rename-resistant
duplicate functions), **dead-code detection**, an internal import dependency graph
with circular-import detection, **baseline & trend-history tracking with sparklines**,
a 0–100 health score, **markdown PR reports and an SVG badge**, and a beautiful
self-contained HTML report with an **SVG dependency graph, codebase treemap and
health-trend chart** — using nothing but the Python standard library.

![CI](https://github.com/Ibnuawf/codi/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen)

## Why

Tools like radon, flake8 and pylint each answer one question. Codi answers the
question engineering managers actually ask — *"how healthy is this codebase and
what should we fix first?"* — in one command, with no dependencies to install,
and a report you can attach to a PR or email to a stakeholder.

## Install

```bash
pip install .
# or run straight from source — no install, no dependencies:
python -m codi path/to/project
```

## Usage

```bash
codi src/                          # terminal health summary
codi src/ --html report.html       # self-contained HTML report (dark UI, SVG charts)
codi src/ --json -                 # machine-readable output to stdout
codi src/ --fail-under 70          # CI quality gate: exit 2 if health < 70
codi src/ --save-baseline base.json    # snapshot today's metrics
codi src/ --baseline base.json         # show ✓/✗ deltas vs the snapshot
codi src/ --min-clone-size 6           # tune clone detection sensitivity
codi src/ --md -                       # markdown report to stdout (paste into a PR)
codi src/ --badge health.svg           # shields-style SVG badge for your README
codi src/ --history codi-history.json  # append run to trend log (sparkline + HTML chart)
codi src/ --churn-since "3 months"     # churn window for git risk analysis
codi src/ --no-churn                   # skip git churn analysis
```

Example terminal output:

```
  Codi v1.0.0 — /home/dev/myproject
  ────────────────────────────────────────────────────────────
  Health  ██████████████████████████░░░░  87.4/100  grade B
  Files: 24   SLOC: 3,182   Functions: 141   Avg CC: 3.1
  Docstrings: 78%   Import cycles: 0   Parse errors: 0

  Top refactoring hotspots:
   🟠 OrderService.process  (services/orders.py:112)  CC=23  — complexity 23 (grade C); 88 lines long
   🟡 parse_config  (config.py:40)  CC=14  — complexity 14 (grade C); complex but undocumented
```

## What it measures

| Signal | How |
|---|---|
| **Cyclomatic complexity** | AST visitor counting decision points per function (if/loops/except/bool-ops/ternaries/comprehension filters/match cases), nested functions measured separately |
| **Cognitive complexity** | Sonar-style readability cost: each flow break costs 1, nested breaks cost more, `elif`/`else` a flat +1 — measures how hard code is for a *human*, not a machine |
| **Type-hint coverage** | Share of functions with complete annotations (all params + return; `self`/`cls` exempt) |
| **Halstead volume + real MI** | Operator/operand counts feed the classic maintainability-index formula per file |
| **Refactoring hotspots** | Blended risk score from complexity, function length, parameter count, and missing docs |
| **Clone detection** | Functions with structurally identical ASTs after normalizing identifiers and constants — catches renamed copy-pastes (type-2 clones) |
| **Dead code** | Whole-project reference analysis flags functions never used as a call, attribute, decorator, export or `__all__` string; convention names (`main`, `test_*`, dunders) exempt |
| **Baselines** | `--save-baseline`/`--baseline` snapshot metrics to JSON and print improved/regressed deltas — track health over time or across a PR |
| **Churn risk** | `git log` change frequency per file × average complexity — hot **and** complex files are ranked as the most likely source of the next bug (degrades gracefully without git) |
| **Trend history** | `--history` appends every run to a JSON log; terminal sparkline (`▅▆▇`) and an SVG line chart in the HTML report |
| **Import graph** | Internal module dependency edges, fan-in/fan-out, and **elementary cycle detection** via DFS — rendered as an interactive circular SVG graph in the HTML report (red edges = cycles) |
| **Codebase treemap** | SVG treemap in the HTML report: area = SLOC, color = average complexity — see your risk surface at a glance |
| **PR integration** | `--md` writes a GitHub-flavored markdown summary (score, deltas, hotspots, churn) ready to paste into a PR comment; `--badge` emits a shields-style SVG |
| **GitHub annotations** | Inside GitHub Actions (or with `--gha`), hotspots, dead code, clones and cycles are emitted as `::warning` commands — they appear inline on the PR's changed files, no marketplace action needed |
| **Refactoring advice** | Every hotspot comes with the single best next action ("flatten nesting: use guard clauses", "group parameters into a dataclass") in terminal, HTML, markdown and JSON output |

## Configuration

Commit your thresholds once instead of repeating flags — `codi.toml` in the
project root (or a `[tool.codi]` table in `pyproject.toml`); CLI flags always
win (Python 3.11+; ignored on 3.10):

```toml
# codi.toml
fail_under = 70
min_clone_size = 4
churn_since = "6 months"
```
| **Maintainability index** | Classic MI formula normalised to 0–100 per file |
| **Health score** | 100-point blend: complexity (35) + hotspot density (20) + documentation (15) + import structure (10) + duplication (10) + dead code (10), minus parse-error penalties |

## CI quality gate

Codi gates its own CI with itself:

```yaml
- name: Code health gate
  run: python -m codi src/ --fail-under 70
```

## Design notes

- **Stdlib only, by design.** Runs anywhere Python 3.10+ runs — air-gapped
  servers, CI containers, a fresh laptop — with zero supply-chain surface.
- **Single-pass AST analysis.** Each file is parsed once; complexity, structure,
  imports and docs are extracted from the same tree.
- **Self-contained reports.** The HTML report embeds all CSS and SVG inline —
  one file you can attach, host, or open offline.
- **Tested.** 49 unit tests cover the complexity visitor, analyzer, graph
  algorithms, clone/dead-code detectors, baselines, churn ranking, history,
  markdown/badge/SVG renderers and scoring; CI runs the
  matrix on Linux + Windows across Python 3.10–3.13, then runs Codi on itself
  as a quality gate.
- **Dogfooded.** v2's own clone and dead-code detectors flagged real issues in
  Codi v1's code — eight structurally identical AST visitor methods and two
  unused functions — which drove the v2 refactor. The gate keeps it honest.

## License

MIT © Abdurehman Muhammed
