# Codi 🩺

**Zero-dependency Python code-health analyzer.** One command gives you cyclomatic
complexity per function, refactoring hotspots ranked by risk, an internal import
dependency graph with circular-import detection, a 0–100 health score, and a
beautiful self-contained HTML report — using nothing but the Python standard library.

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
| **Refactoring hotspots** | Blended risk score from complexity, function length, parameter count, and missing docs |
| **Import graph** | Internal module dependency edges, fan-in/fan-out, and **elementary cycle detection** via DFS |
| **Maintainability index** | Classic MI formula normalised to 0–100 per file |
| **Health score** | 100-point blend: complexity (40) + hotspot density (25) + documentation (20) + import structure (15), minus parse-error penalties |

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
- **Tested.** 25 unit tests cover the complexity visitor, analyzer, graph
  algorithms and scoring; CI runs the matrix on Linux + Windows across
  Python 3.10–3.13, then runs Codi on itself as a quality gate.

## License

MIT © Abdurehman
