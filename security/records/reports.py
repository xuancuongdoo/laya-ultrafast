"""Report derivation: chain + ledger -> schema-shaped report dict.

Schema single source of truth: security/records/schemas/report-schema.json
(title/date/commit/areas/findings/coverage). Field lists are not duplicated
in code beyond the REQUIRED_REPORT_FIELDS cross-check in validate_report.
"""

from __future__ import annotations

import json
import subprocess
from datetime import date
from pathlib import Path

from .chain import verify_chain

REQUIRED_REPORT_FIELDS = ("title", "date", "commit", "areas", "findings", "coverage")


def _commit(repo: str | Path | None = None) -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=repo or Path(__file__).parent.parent.parent,
        )
        sha = out.stdout.strip()
        return sha if out.returncode == 0 and sha else "unknown"
    except OSError:
        return "unknown"


def derive_report(title: str, chain: list[dict], ledger) -> dict:
    """Verify the chain, then build the report dict for one audit title.

    ledger: CoverageLedger for this run; areas/coverage come from it.
    """
    verify_chain(chain)
    chain_areas = {r["area"] for r in chain}
    areas = sorted(chain_areas | set(ledger.areas(title)))
    coverage = round(sum(float(ledger.coverage(a)) for a in areas) / len(areas), 4) if areas else 0.0
    return {
        "title": title,
        "date": date.today().isoformat(),
        "commit": _commit(),
        "areas": areas,
        "findings": [
            {"id": r["id"], "area": r["area"], "severity": r["severity"], "detail": r["detail"]} for r in chain
        ],
        "coverage": coverage,
    }


def validate_report(report: dict, schema_path: str | Path | None = None) -> bool:
    """Shape-check a report; cross-check field list against the JSON schema file."""
    for field in REQUIRED_REPORT_FIELDS:
        if field not in report:
            raise ValueError(f"report missing {field!r}")
    if not isinstance(report["areas"], list) or not report["areas"]:
        raise ValueError("report 'areas' must be a non-empty list")
    if not isinstance(report["findings"], list):
        raise ValueError("report 'findings' must be a list")
    if not 0.0 <= float(report["coverage"]) <= 1.0:
        raise ValueError(f"coverage out of range: {report['coverage']!r}")
    if schema_path is not None:
        schema = json.loads(Path(schema_path).read_text())
        required = set(schema.get("required", []))
        if required and set(REQUIRED_REPORT_FIELDS) != required:
            raise ValueError(
                f"code/schema field drift: code={sorted(REQUIRED_REPORT_FIELDS)} schema={sorted(required)}"
            )
        if required and not required.issubset(set(report)):
            raise ValueError(f"report misses schema fields: {sorted(required - set(report))}")
    return True
