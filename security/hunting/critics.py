"""Critics: findings + ledger -> JSON-serializable coverage verdict."""

from __future__ import annotations

from security.records.chain import SEVERITIES


def critique(target, ledger, findings: list[dict]) -> dict:
    """Verdict over one audit target: coverage, gaps, criticals, severity counts."""
    area = str(target)
    uncovered = [[a, p] for a, p in ledger.uncovered(area)]
    critical = [f["id"] for f in findings if f.get("severity") == "critical"]
    severities: dict[str, int] = {sev: 0 for sev in SEVERITIES}
    for finding in findings:
        sev = finding.get("severity")
        severities[sev] = severities.get(sev, 0) + 1
    notes = [f"{a}::{p} has no coverage" for a, p in uncovered]
    notes.extend(f"critical finding {fid} is open" for fid in critical)
    return {
        "target": area,
        "coverage": float(ledger.coverage(area)),
        "uncovered": uncovered,
        "critical": critical,
        "severities": severities,
        "notes": notes,
    }


__all__ = ["critique"]
