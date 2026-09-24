# Audit Orchestrator

Dispatches security audits per the audit diagram: Parent Coding Agent hands a
title to this orchestrator; it runs injected hunters, filters via validators
against Prior Audit Evidence, verifies the records chain, and derives a
schema-valid report.

## Contract

```python
from security.orchestration.orchestrator import Orchestrator
from security.orchestration.prior_evidence import PriorEvidence
from security.reconnaissance.ledger import CoverageLedger

ledger = CoverageLedger()
ledger.mark("ultrafast/agent.py", "recon")
orch = Orchestrator(
    title="weekly-audit",
    hunters=[
        lambda area, ev: [
            {"id": "H-1", "area": area, "severity": "low", "detail": "open header"},
        ]
    ],
    validators=[lambda finding, ev: not ev.suppress(finding)],
    ledger=ledger,
    evidence=PriorEvidence(),
)
report = orch.run()
assert set(report) == {"title", "date", "commit", "areas", "findings", "coverage"}
```

## Pipeline

1. Load `PriorEvidence` (past runs inform scope, never the report shape).
2. `ledger.validate()` — reject unknown phases/statuses before any work.
3. For each ledger area: run hunters → `verify_finding` each raw finding →
   drop findings any validator rejects → `append` survivors to the
   hash-linked chain → mark all phases `verified`.
4. `verify_chain` the full chain, `derive_report`, `validate_report`.

## Seams (DRY: logic lives in siblings, never here)

- Persistence: `security/orchestration/prior_evidence.py` (`PriorEvidence`).
- Coverage: `security/reconnaissance/ledger.py` (`CoverageLedger`).
- Proof: `security/records/` (`chain.append/verify_chain`, `reports.derive_report`).
- Schema: `security/records/schemas/report-schema.json`.

## Rules

- Hunters/validators are injected via the constructor; the orchestrator never
  hardcodes hunter/validator logic.
- Findings missing `id`/`area`/`severity`/`detail` or with unknown severity
  are rejected before they touch the chain.
- Ledger cells only move `pending -> covered/verified`; `run` marks verified.
- Validator returning False drops the finding silently (validated out).
