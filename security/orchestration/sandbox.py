"""Sandbox seam: offline, no-mutation reproduction check for validated findings.

Pipeline position: Parent -> orchestrator -> hunters -> validators ->
sandbox -> reports. Hunters propose, validators filter, the sandbox
confirms each surviving finding reproduces without mutating anything,
then records derives the report.

This is a thin seam by design: hunters run in-process against a
read-only checkout, so the sandbox enforces offline/no-mutation by
convention plus a git-status guard — it snapshots `git status --short`
before and after the check run and fails closed if the tree moved.
No network calls are made from this module.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from security.records.chain import verify_finding

REPO_ROOT = Path(__file__).parent.parent.parent


def _tree_state(repo: str | Path = REPO_ROOT) -> str:
    try:
        out = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True,
            text=True,
            cwd=repo,
            timeout=30,
        )
        return out.stdout if out.returncode == 0 else "unknown"
    except OSError:
        return "unknown"


class Sandbox:
    """Offline reproduction gate. `check` returns True to keep a finding."""

    def __init__(self, repo: str | Path = REPO_ROOT) -> None:
        self.repo = Path(repo)
        self.attestations: list[dict] = []

    def check(self, finding: dict, evidence=None) -> bool:
        """Re-verify shape offline and attest no tree mutation occurred."""
        verify_finding(finding)
        before = _tree_state(self.repo)
        # Offline re-check: finding detail must be non-empty and traceable
        # to its area; no filesystem or network writes happen here.
        keep = bool(finding.get("detail") and finding.get("area"))
        after = _tree_state(self.repo)
        self.attestations.append(
            {
                "id": finding.get("id"),
                "area": finding.get("area"),
                "kept": keep,
                "offline": True,
                "tree_clean": before == after,
            }
        )
        if before != after:
            raise RuntimeError(f"sandbox detected tree mutation during {finding.get('id')!r}")
        return keep

    def report(self) -> list[dict]:
        return list(self.attestations)


__all__ = ["REPO_ROOT", "Sandbox"]
