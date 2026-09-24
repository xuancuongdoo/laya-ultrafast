"""Offline static architecture map: index *.py, packages, entry points, tests.

Stdlib only. No network, no browser, no paid APIs, no credentials.
"""

from __future__ import annotations

import json
import os
import tomllib
from datetime import datetime, timezone
from pathlib import Path

SKIP_DIRS = frozenset({".venv", "__pycache__", ".git", "node_modules", "dist", "recordings"})


def _walk(root: Path):
    """Yield (dirpath, filenames) with SKIP_DIRS pruned, in sorted order."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        yield Path(dirpath), sorted(filenames)


def _package(root: Path, file: Path) -> str | None:
    """Dotted name of the nearest ancestor-or-self dir holding __init__.py, else None."""
    try:
        rel = file.parent.relative_to(root)
    except ValueError:
        return None
    for depth in range(len(rel.parts), 0, -1):
        if (root.joinpath(*rel.parts[:depth]) / "__init__.py").is_file():
            return ".".join(rel.parts[:depth])
    return None


def _packages(root: Path) -> list[str]:
    """Dirs holding __init__.py plus their namespace parents (e.g. backends)."""
    found: set[str] = set()
    for dirpath, filenames in _walk(root):
        if "__init__.py" not in filenames:
            continue
        rel = dirpath.relative_to(root)
        if not rel.parts:
            continue
        for depth in range(1, len(rel.parts) + 1):
            found.add(".".join(rel.parts[:depth]))
    return sorted(found)


def _modules(root: Path) -> list[dict]:
    modules = []
    for dirpath, filenames in _walk(root):
        for name in filenames:
            if not name.endswith(".py"):
                continue
            file = dirpath / name
            try:
                lines = len(file.read_text(encoding="utf-8", errors="replace").splitlines())
            except OSError:
                lines = 0
            modules.append(
                {
                    "path": file.relative_to(root).as_posix(),
                    "package": _package(root, file),
                    "lines": lines,
                }
            )
    return sorted(modules, key=lambda m: m["path"])


def _console_scripts(root: Path) -> list[str]:
    try:
        data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return []
    if not isinstance(data, dict):
        return []
    project = data.get("project", {})
    if not isinstance(project, dict):
        return []
    scripts = project.get("scripts", {})
    if not isinstance(scripts, dict):
        return []
    return [f"{name} = {target}" for name, target in sorted(scripts.items())]


def _entry_points(root: Path) -> list[str]:
    points = _console_scripts(root)
    points.extend(sorted(p.relative_to(root).as_posix() for p in root.glob("demos/*/run.py") if p.is_file()))
    if (root / "ultrafast" / "demo.py").is_file():
        points.append("ultrafast/demo.py")
    return points


def _tests(root: Path) -> list[str]:
    return sorted(p.relative_to(root).as_posix() for p in root.glob("tests/test_*.py") if p.is_file())


def recon(target_root, ledger=None) -> dict:
    """Build the JSON-serializable Architecture Map for target_root.

    target is the audit label (str of target_root as given); root is the
    resolved absolute path. Marks (target, recon) verified on ledger if given.
    """
    root = Path(target_root)
    area = str(target_root)
    if ledger is not None:
        ledger.mark(area, "recon", "verified")
    return {
        "target": area,
        "root": str(root.resolve()),
        "modules": _modules(root),
        "packages": _packages(root),
        "entry_points": _entry_points(root),
        "tests": _tests(root),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def save_map(map: dict, path) -> Path:
    """Write an Architecture Map as indented JSON, creating parents."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(map, indent=2))
    return dest


__all__ = ["SKIP_DIRS", "recon", "save_map"]
