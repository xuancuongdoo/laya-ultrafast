"""Audit Orchestrator: run hunters -> validators -> schema-valid report.

Contract (single reconciled shape):
    Orchestrator(title, hunters, validators).run() -> report dict

- hunter(area, evidence) -> list[finding]: recon finding producers.
  finding shape: {id, area, severity, detail} (see report-schema.json).
- validator(finding, evidence) -> bool: True keeps the finding, False drops
  it (validated out, e.g. duplicate of prior evidence or false positive).

Pipeline: for each area of the ledger run hunters, drop findings rejected
by any validator, verify + hash-link survivors into the records chain, mark
all phases verified, then derive and schema-validate the report
(title/date/commit/areas/findings/coverage).

Prior evidence informs scope (hunters/validators read it) but never the
shape — the report always carries the full schema fields.
"""

from __future__ import annotations

from pathlib import Path

from security.reconnaissance.ledger import PHASES, CoverageLedger
from security.records import append, derive_report, validate_report, verify_chain, verify_finding

from .prior_evidence import PriorEvidence

SCHEMA_PATH = Path(__file__).parent.parent / "records" / "schemas" / "report-schema.json"


class Orchestrator:
    def __init__(
        self,
        title: str,
        hunters: list | None = None,
        validators: list | None = None,
        ledger: CoverageLedger | None = None,
        evidence: PriorEvidence | None = None,
    ) -> None:
        if not title:
            raise ValueError("title must be non-empty")
        self.title = title
        self.hunters = list(hunters or [])
        self.validators = list(validators or [])
        self.ledger = ledger or CoverageLedger()
        self.evidence = evidence or PriorEvidence()

    def run(self) -> dict:
        """Run hunters -> validators for every area; return the validated report."""
        self.ledger.validate()
        areas = self.ledger.areas(self.title) or [self.title]
        chain: list[dict] = []
        for area in areas:
            for hunter in self.hunters:
                for raw in hunter(area, self.evidence) or []:
                    finding = dict(raw)
                    finding.setdefault("area", area)
                    verify_finding(finding)
                    if all(v(finding, self.evidence) for v in self.validators):
                        append(chain, finding)
            for phase in PHASES:
                self.ledger.mark(area, phase, "verified")
        verify_chain(chain)
        report = derive_report(self.title, chain, self.ledger)
        validate_report(report, SCHEMA_PATH)
        return report


__all__ = ["SCHEMA_PATH", "Orchestrator"]
