"""Offline: recon map + hunting playbooks + critics, no network, no paid APIs."""

import json
from pathlib import Path

from security.hunting.critics import critique
from security.hunting.playbooks import PLAYBOOKS, done_safety, prompt_injection, run_all, secrets
from security.reconnaissance.ledger import CoverageLedger
from security.reconnaissance.phase import recon, save_map
from security.records.chain import append, verify_chain, verify_finding

REPO = Path(__file__).resolve().parent.parent


def _fixture_repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pkg").mkdir(exist_ok=True)
    (root / "pkg" / "__init__.py").write_text("")
    (root / "pkg" / "mod.py").write_text("X = 1\n")
    (root / "plain.py").write_text("Y = 2\n")
    (root / "pyproject.toml").write_text('[project]\nname = "fx"\n[project.scripts]\nfx = "pkg.mod:main"\n')
    (root / "demos" / "alpha").mkdir(parents=True)
    (root / "demos" / "alpha" / "run.py").write_text("def verify(agent):\n    assert agent\n")
    (root / "ultrafast").mkdir()
    (root / "ultrafast" / "demo.py").write_text("# demo\n")
    (root / "tests").mkdir()
    (root / "tests" / "test_alpha.py").write_text("def test_x():\n    assert True\n")
    (root / ".venv").mkdir()
    (root / ".venv" / "evil.py").write_text("Z = 3\n")
    return root


def test_recon_fixture_map_and_ledger(tmp_path):
    root = _fixture_repo(tmp_path / "fx")
    ledger = CoverageLedger()
    arch = recon(root, ledger)
    assert set(arch) == {"target", "root", "modules", "packages", "entry_points", "tests", "generated_at"}
    by_path = {m["path"]: m for m in arch["modules"]}
    assert {"pkg/mod.py", "pkg/__init__.py", "plain.py", "demos/alpha/run.py"} <= set(by_path)
    assert ".venv/evil.py" not in by_path
    assert by_path["pkg/mod.py"]["package"] == "pkg"
    assert by_path["plain.py"]["package"] is None
    assert by_path["pkg/mod.py"]["lines"] == 1
    assert "pkg" in arch["packages"]
    assert "fx = pkg.mod:main" in arch["entry_points"]
    assert "demos/alpha/run.py" in arch["entry_points"]
    assert "ultrafast/demo.py" in arch["entry_points"]
    assert arch["tests"] == ["tests/test_alpha.py"]
    assert ledger.status(str(root), "recon") == "verified"
    json.dumps(arch)  # JSON-serializable


def test_recon_save_load_roundtrip(tmp_path):
    root = _fixture_repo(tmp_path / "fx")
    arch = recon(root)
    dest = save_map(arch, root / "out" / "map.json")
    assert isinstance(dest, Path) and dest.is_file()
    assert json.loads(dest.read_text()) == arch


def test_recon_real_root_finds_core_packages():
    arch = recon(REPO)
    assert "ultrafast" in arch["packages"]
    assert "backends" in arch["packages"]
    assert arch["modules"]


def test_playbooks_chain_compatible_on_real_root():
    assert set(PLAYBOOKS) == {"secrets", "prompt_injection", "done_safety"}
    for run in PLAYBOOKS.values():
        chain: list = []
        for finding in run(REPO):
            assert verify_finding(finding) is True
            append(chain, finding)
        assert verify_chain(chain) is True


def test_secrets_zero_high_critical_on_real_root():
    bad = [f for f in secrets.run(REPO) if f["severity"] in ("high", "critical")]
    assert bad == []


def test_secrets_fixture_flags_paths_only(tmp_path):
    root = tmp_path / "fx"
    (root / ".gitignore").parent.mkdir(parents=True)
    (root / ".gitignore").write_text(".env\n")
    (root / ".env").write_text("SENTINEL_VALUE_1=abc123\n")
    (root / "api_secret_backup.txt").write_text("SENTINEL_VALUE_2=def456\n")
    (root / "server.pem").write_text("SENTINEL_VALUE_3=ghi789\n")
    findings = {f["id"]: f for f in secrets.run(root)}
    assert findings["SEC-DOTENV-1"]["severity"] == "info"  # gitignored via fallback parse
    assert findings["SEC-KEY-1"]["severity"] == "high"
    assert any(f["severity"] == "medium" for f in findings.values())
    for finding in findings.values():
        assert "SENTINEL" not in json.dumps(finding)  # paths only, never contents


def test_secrets_dotenv_tracked_is_high(tmp_path):
    root = tmp_path / "fx"
    root.mkdir()
    (root / ".env").write_text("")
    findings = secrets.run(root)
    assert [(f["id"], f["severity"]) for f in findings] == [("SEC-DOTENV-1", "high")]


def test_prompt_injection_boundary_holds():
    assert prompt_injection.run(REPO) == []


def test_done_safety_behavioral_probes_hold():
    behavioral = [f for f in done_safety.run(REPO) if not f["id"].startswith("DS-VERIFY-")]
    assert behavioral == []


def test_done_safety_static_gate_fixture(tmp_path):
    root = tmp_path / "fx"
    (root / "demos" / "good").mkdir(parents=True)
    (root / "demos" / "good" / "run.py").write_text("def verify(agent):\n    assert agent\n")
    (root / "demos" / "bad").mkdir(parents=True)
    (root / "demos" / "bad" / "run.py").write_text("print('no gate')\n")
    static = {f["id"]: f for f in done_safety.run(root) if f["id"].startswith("DS-VERIFY-")}
    assert set(static) == {"DS-VERIFY-bad"}
    assert static["DS-VERIFY-bad"]["severity"] == "medium"


def test_critique_reflects_gaps_and_criticals():
    ledger = CoverageLedger()
    ledger.mark("t", "recon", "verified")
    findings = [
        {"id": "X-1", "target": "t", "area": "t", "severity": "critical", "detail": "boom"},
        {"id": "X-2", "target": "t", "area": "t", "severity": "low", "detail": "note"},
    ]
    verdict = critique("t", ledger, findings)
    assert set(verdict) == {"target", "coverage", "uncovered", "critical", "severities", "notes"}
    assert verdict["target"] == "t"
    assert verdict["coverage"] == 0.25
    assert verdict["uncovered"] == [["t", "hunt"], ["t", "verify"], ["t", "report"]]
    assert verdict["critical"] == ["X-1"]
    assert verdict["severities"]["critical"] == 1
    assert verdict["severities"]["low"] == 1
    assert verdict["notes"] and all(isinstance(n, str) for n in verdict["notes"])
    json.dumps(verdict)  # JSON-serializable


def test_run_all_aggregates_playbooks_with_prefixes():
    assert run_all(REPO) == secrets.run(REPO) + prompt_injection.run(REPO) + done_safety.run(REPO)
    for finding in run_all(REPO):
        assert finding["id"].startswith(("SEC-", "PI-", "DS-"))
