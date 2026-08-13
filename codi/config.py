"""Project config: `codi.toml` or `[tool.codi]` in pyproject.toml.

CLI flags always win; the config file only supplies defaults, so a team
can commit its thresholds once instead of repeating flags in every
invocation. Uses stdlib tomllib (Python 3.11+); on 3.10 config files are
silently ignored and flags keep working.
"""

from __future__ import annotations

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    tomllib = None

# config key -> argparse dest (all optional)
_KEYS = {
    "fail_under": "fail_under",
    "min_clone_size": "min_clone_size",
    "churn_since": "churn_since",
    "no_churn": "no_churn",
    "history": "history",
    "baseline": "baseline",
}


def load_config(root: Path) -> dict:
    """Read codi settings from codi.toml or pyproject.toml [tool.codi]."""
    if tomllib is None:
        return {}
    base = root if root.is_dir() else root.parent
    for candidate, keys in (
        (base / "codi.toml", ()),
        (base / "pyproject.toml", ("tool", "codi")),
        (Path.cwd() / "codi.toml", ()),
        (Path.cwd() / "pyproject.toml", ("tool", "codi")),
    ):
        try:
            data = tomllib.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            continue
        for key in keys:
            data = data.get(key, {})
        if data:
            return {v: data[k] for k, v in _KEYS.items() if k in data}
    return {}


def apply_config(args, config: dict, parser_defaults: dict) -> None:
    """Fill args with config values wherever the flag was left at default."""
    for dest, value in config.items():
        if getattr(args, dest, None) == parser_defaults.get(dest):
            setattr(args, dest, value)
