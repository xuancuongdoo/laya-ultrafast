"""Security layer: orchestrator(title, hunters, validators).run() + ledger + chain."""

from security.orchestration.orchestrator import SCHEMA_PATH, Orchestrator
from security.orchestration.prior_evidence import PriorEvidence
from security.reconnaissance.ledger import CoverageLedger
from security.records import append, validate_report, verify_chain


def test_ledger_mark_and_coverage():
    ledger = CoverageLedger()
    assert ledger.coverage("t") == 0.0
    ledger.mark("t", "recon")
    ledger.mark("t", "hunt", "verified")
    assert ledger.status("t", "recon") == "covered"
    assert ledger.coverage("t") == 0.5
    assert ledger.uncovered("t") == [("t", "verify"), ("t", "report")]
    ledger.validate()


def test_prior_evidence_roundtrip(tmp_path):
    store = PriorEvidence()
    store.add({"id": "a1", "target": "t"})
    path = store.save(tmp_path / "prior.json")
    assert PriorEvidence(path).get("t") == [{"id": "a1", "target": "t"}]


def test_chain_tamper_detected():
    chain: list = []
    append(chain, {"id": "F-1", "area": "t", "severity": "low", "detail": "d"})
    assert verify_chain(chain) is True
    chain[0]["detail"] = "tampered"
    try:
        verify_chain(chain)
        raise AssertionError("tamper passed")
    except ValueError:
        pass


def _hunter(area, evidence):
    return [{"id": "H-1", "area": area, "severity": "low", "detail": "d"}]


def test_orchestrator_run_contract():
    ledger = CoverageLedger()
    ledger.mark("t", "recon")
    orch = Orchestrator(title="weekly-audit", hunters=[_hunter], ledger=ledger)
    report = orch.run()
    assert report["title"] == "weekly-audit"
    assert set(report) == {"title", "date", "commit", "areas", "findings", "coverage"}
    assert report["areas"] == ["t"]
    assert report["coverage"] == 1.0
    assert report["findings"][0]["id"] == "H-1"
    assert validate_report(report, SCHEMA_PATH) is True


def test_orchestrator_validator_drops_finding():
    ledger = CoverageLedger()
    ledger.mark("t", "recon")
    orch = Orchestrator(
        title="weekly-audit",
        hunters=[_hunter],
        validators=[lambda finding, ev: False],
        ledger=ledger,
    )
    report = orch.run()
    assert report["findings"] == []
    assert report["coverage"] == 1.0
