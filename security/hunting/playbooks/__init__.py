"""Playbook registry: secrets, prompt_injection, done_safety."""

from __future__ import annotations

from . import done_safety, prompt_injection, secrets

PLAYBOOKS = {
    "secrets": secrets.run,
    "prompt_injection": prompt_injection.run,
    "done_safety": done_safety.run,
}


def run_all(target_root) -> list[dict]:
    """Run every playbook over target_root; finding ids carry per-playbook prefixes."""
    findings: list[dict] = []
    for run in PLAYBOOKS.values():
        findings.extend(run(target_root))
    return findings


__all__ = ["PLAYBOOKS", "done_safety", "prompt_injection", "run_all", "secrets"]
