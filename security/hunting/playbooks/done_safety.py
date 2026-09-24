"""DONE-requires-evidence invariant: behavioral mock probes + static demo gate.

choose must reach DONE only when the quoted target is visibly satisfied
at the arrived URL with disambiguator words present; a
wrong-disambiguation slug page must never yield DONE. Statically, every
demos/*/run.py must define def verify() containing assert statements.
"""

from __future__ import annotations

import ast
from pathlib import Path

from backends.mock.model import choose

GOAL = 'Search for "Ada Lovelace" and open the mathematician article.'
HISTORY = [{"choice": "e1", "kind": "fill"}]


def _finding(target: str, fid: str, severity: str, detail: str) -> dict:
    # area mirrors target: chain.verify_finding requires area, audit shape wants target.
    return {"id": fid, "target": target, "area": target, "severity": severity, "detail": detail}


def _actions():
    return [
        {"id": "e1", "kind": "fill", "label": "Search Wikipedia", "node": 1, "value": ""},
        {"id": "e2", "kind": "click", "label": "Ada Lovelace", "node": 2},
        {"id": "e3", "kind": "click", "label": "Computer hardware", "node": 3},
    ]


def _behavioral() -> list[tuple[str, str, str]]:
    """(finding id, severity, detail) triples, one per violated probe."""
    violated: list[tuple[str, str, str]] = []
    satisfied = {
        "url": "https://en.wikipedia.org/wiki/Ada_Lovelace",
        "title": "Ada Lovelace - Wikipedia",
        "text": "Ada Lovelace English mathematician Analytical Engine",
        "actions": _actions(),
    }
    if choose(satisfied, GOAL, HISTORY)["choice"] != "DONE":
        violated.append(
            ("DS-DONE-MISSING-1", "medium", "choose missed DONE despite satisfied evidence at the arrived URL")
        )
    wrong_slug = {
        "url": "https://en.wikipedia.org/wiki/Ada_Lovelace_(microarchitecture)",
        "title": "Ada Lovelace (microarchitecture) - Wikipedia",
        "text": "Ada Lovelace microarchitecture Nvidia mathematician graphics design",
        "actions": _actions(),
    }
    if choose(wrong_slug, GOAL, HISTORY)["choice"] == "DONE":
        violated.append(("DS-FALSE-DONE-SLUG-1", "high", "choose returned DONE on a wrong-disambiguation slug page"))
    no_disambiguator = {
        "url": "https://en.wikipedia.org/wiki/Ada_Lovelace",
        "title": "Ada Lovelace - Wikipedia",
        "text": "Ada Lovelace notes Analytical Engine translation",
        "actions": _actions(),
    }
    if choose(no_disambiguator, GOAL, HISTORY)["choice"] == "DONE":
        violated.append(
            ("DS-FALSE-DONE-DISAMBIG-1", "high", "choose returned DONE without disambiguator words present")
        )
    return violated


def _has_verify_with_asserts(run_py: Path) -> bool:
    """True when run.py defines top-level def verify() containing an assert."""
    try:
        tree = ast.parse(run_py.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError):
        return False
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "verify":
            return any(isinstance(n, ast.Assert) for n in ast.walk(node))
    return False


def _static(root: Path) -> list[tuple[str, str]]:
    """(demo name, rel path) pairs missing a verifiable def verify()."""
    missing = []
    for run_py in sorted(root.glob("demos/*/run.py")):
        if run_py.is_file() and not _has_verify_with_asserts(run_py):
            missing.append((run_py.parent.name, run_py.relative_to(root).as_posix()))
    return missing


def run(target_root) -> list[dict]:
    """Probe DONE-evidence behaviorally, then gate every demo statically."""
    root = Path(target_root)
    target = str(target_root)
    findings = [_finding(target, fid, sev, detail) for fid, sev, detail in _behavioral()]
    for demo, rel in _static(root):
        findings.append(_finding(target, f"DS-VERIFY-{demo}", "medium", f"{rel}: missing def verify() with asserts"))
    return findings


__all__ = ["GOAL", "HISTORY", "run"]
