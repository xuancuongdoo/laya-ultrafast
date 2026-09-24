"""Verified records chain: hash-linked findings + chain verification.

Finding shape (single source of truth, mirrors
security/records/schemas/report-schema.json): id/area/severity/detail.
"""

from __future__ import annotations

import hashlib

SEVERITIES = ("info", "low", "medium", "high", "critical")
REQUIRED = ("id", "area", "severity", "detail")
GENESIS_PREV = "GENESIS"


def _digest(prev: str, finding: dict) -> str:
    payload = "|".join([prev, finding["id"], finding["area"], finding["severity"], finding["detail"]])
    return hashlib.sha256(payload.encode()).hexdigest()


def verify_finding(finding: dict) -> bool:
    """Check one finding has required fields and a known severity."""
    for field in REQUIRED:
        if not finding.get(field):
            raise ValueError(f"finding missing {field!r}: {finding!r}")
    if finding["severity"] not in SEVERITIES:
        raise ValueError(f"unknown severity {finding['severity']!r}")
    return True


def append(chain: list[dict], finding: dict) -> dict:
    """Validate a finding and link it onto the chain. Returns the record."""
    verify_finding(finding)
    prev = chain[-1]["digest"] if chain else GENESIS_PREV
    record = {k: finding[k] for k in REQUIRED}
    record["prev"] = prev
    record["digest"] = _digest(prev, record)
    chain.append(record)
    return record


def verify_chain(chain: list[dict]) -> bool:
    """Recompute every link. Raises on first tamper, True when clean."""
    prev = GENESIS_PREV
    for record in chain:
        verify_finding(record)
        if record.get("prev") != prev:
            raise ValueError(f"chain link broken at {record.get('id')!r}")
        if record.get("digest") != _digest(prev, record):
            raise ValueError(f"chain digest mismatch at {record.get('id')!r}")
        prev = record["digest"]
    return True
