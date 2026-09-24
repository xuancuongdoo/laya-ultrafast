# TESTING.md — security rework (t_bebd6f8f)

Target: /Users/xuancuong/laya-ultrafast. Contract unchanged:
Orchestrator(title, hunters, validators).run() -> report
{title, date, commit, areas, findings, coverage}.

## Fixes (vs gate t_6dc4b2c2 FAIL)

1. records import: reconciled records/__init__.py and reports.py already
   carry no VERDICTS import — import succeeds (verified below).
2. Coverage scope: reports.derive_report averages ledger.coverage(a) over
   the run's areas (chain areas ∪ ledger areas for the title), not over
   the title string. This run additionally unions so zero-finding areas
   stay in the report.
3. Sandbox stage: added security/orchestration/sandbox.py — thin
   offline/no-mutation runner (shape re-check + git-status guard, no
   network/file writes). Pipeline: Parent -> orchestrator -> hunters ->
   validators -> sandbox -> reports. run_audit.py wires it as a validator.
4. Naming drift: documented in PriorEvidence docstring — entries key on
   'target' (past-run scope lookup), live findings key on 'area'
   (chain REQUIRED field); validators bridge the two.

## Commands + outputs (2026-09-23)

$ uv run python -c "from security.orchestration.orchestrator import Orchestrator"
import ok

$ uv run pytest
27 passed in 0.10s (test_hunting 12, test_mock_backend 8,
test_security_layer 5, test_shortlist 2)

$ uv run ruff check .
All checks passed!

$ uv run ruff format --check .
46 files already formatted

$ uv run python security/run_audit.py
areas=34 findings=8 coverage=1.0 sandbox_checks=8
report -> /Users/xuancuong/laya-ultrafast/security/audit-report.json

## Report artifact

- security/audit-report.json (schema-valid per validate_report against
  security/records/schemas/report-schema.json): title weekly-audit,
  commit 9991e59, 34 areas, 8 findings (all info/medium network-fetch
  pattern hits on urllib call sites), coverage 1.0.
- Runner: security/run_audit.py [--title T] [--out PATH].
