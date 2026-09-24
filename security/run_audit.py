"""Full security audit loop over the laya-ultrafast repo.

Real hunters scan repo areas (py source for risky patterns), validators
drop false positives/duplicates, the sandbox confirms offline/no-mutation,
then Orchestrator derives + schema-validates the report.

Usage: uv run python security/run_audit.py [--title weekly-audit] [--out security/audit-report.json]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from security.orchestration.orchestrator import SCHEMA_PATH, Orchestrator
from security.orchestration.prior_evidence import PriorEvidence
from security.orchestration.sandbox import Sandbox
from security.reconnaissance.ledger import CoverageLedger
from security.records import validate_report

REPO_ROOT = Path(__file__).parent.parent

PATTERNS = [
    ("subprocess-shell", re.compile(r"shell\s*=\s*True"), "medium"),
    ("eval-use", re.compile(r"(?<![\w.])eval\s*\("), "high"),
    ("exec-use", re.compile(r"(?<![\w.])exec\s*\("), "high"),
    ("pickle-load", re.compile(r"pickle\.loads?\s*\("), "high"),
    ("hardcoded-secret", re.compile(r"(?i)(api[_-]?key|secret|password)\s*=\s*['\"][^'\"]+['\"]"), "medium"),
    ("network-fetch", re.compile(r"(urllib|requests\.get|urlopen)\s*[\.(]"), "info"),
    ("todo-marker", re.compile(r"#\s*(TODO|FIXME|XXX)"), "info"),
]


def make_hunter(root: Path = REPO_ROOT):
    def hunter(area: str, evidence=None) -> list[dict]:
        path = root / area
        if not path.is_file() or path.suffix != ".py":
            return []
        try:
            text = path.read_text()
        except OSError:
            return []
        findings = []
        for lineno, line in enumerate(text.splitlines(), 1):
            for name, rx, severity in PATTERNS:
                if rx.search(line):
                    findings.append(
                        {
                            "id": f"{area}:{lineno}:{name}",
                            "area": area,
                            "severity": severity,
                            "detail": f"{name} at {area}:{lineno}: {line.strip()[:120]}",
                        }
                    )
        return findings

    return hunter


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", default="weekly-audit")
    ap.add_argument("--out", default="security/audit-report.json")
    args = ap.parse_args()

    areas = sorted(
        str(p.relative_to(REPO_ROOT))
        for p in REPO_ROOT.rglob("*.py")
        if ".venv" not in p.parts and "__pycache__" not in p.parts
    )
    ledger = CoverageLedger()
    for area in areas:
        ledger.mark(area, "recon")

    evidence = PriorEvidence()
    sandbox = Sandbox(REPO_ROOT)
    orch = Orchestrator(
        title=args.title,
        hunters=[make_hunter()],
        validators=[
            lambda finding, ev: not ev.suppress(finding),
            lambda finding, ev: sandbox.check(finding, ev),
        ],
        ledger=ledger,
        evidence=evidence,
    )
    report = orch.run()
    assert validate_report(report, SCHEMA_PATH) is True

    out = REPO_ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(
        f"areas={len(report['areas'])} findings={len(report['findings'])} "
        f"coverage={report['coverage']} sandbox_checks={len(sandbox.report())}"
    )
    print(f"report -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
