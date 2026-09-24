"""Playbook registry: ordered map of playbook name -> run callable."""

from __future__ import annotations

from security.hunting.playbooks.done_safety import run as done_safety_run
from security.hunting.playbooks.prompt_injection import run as prompt_injection_run
from security.hunting.playbooks.secrets import run as secrets_run

PLAYBOOKS = {
    "secrets": secrets_run,
    "prompt_injection": prompt_injection_run,
    "done_safety": done_safety_run,
}


def run_all(target_root) -> list[dict]:
    """Run every playbook over target_root; finding ids carry per-playbook prefixes."""
    findings: list[dict] = []
    for run in PLAYBOOKS.values():
        findings.extend(run(target_root))
    return findings


__all__ = ["PLAYBOOKS", "run_all"]
