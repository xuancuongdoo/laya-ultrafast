"""Prior Audit Evidence store: file-backed record of past audit runs.

Deep-nested layout keeps the orchestrator thin: this module owns only
persistence + lookup of prior evidence. Validation lives in records/.
"""

from __future__ import annotations

import json
from pathlib import Path


class PriorEvidence:
    """JSON-backed store of prior audit evidence entries.

    Entry shape: {"id": str, "target": str, ...extra}.

    Naming note: entries key on 'target' (the audit scope a past run
    covered, e.g. "weekly-audit" or a repo path), while live findings
    in security/records/chain.py key on 'area' (where the finding was
    found). 'target' is the lookup key for past runs; 'area' is the
    location field on findings. Validators bridge the two, e.g. by
    matching finding["area"] against entry["target"] or by id.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else None
        self._entries: list[dict] = []
        if self.path and self.path.exists():
            self.load(self.path)

    def load(self, path: str | Path) -> list[dict]:
        self.path = Path(path)
        raw = json.loads(self.path.read_text())
        if isinstance(raw, dict) and "audits" in raw:
            raw = raw["audits"]
        if not isinstance(raw, list):
            raise ValueError("prior evidence file must hold a list or {'audits': [...]}")
        self._entries = list(raw)
        return self._entries

    def save(self, path: str | Path | None = None) -> Path:
        dest = Path(path) if path else self.path
        if dest is None:
            raise ValueError("no path to save prior evidence to")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps({"audits": self._entries}, indent=2))
        self.path = dest
        return dest

    def add(self, entry: dict) -> dict:
        if not entry.get("id") or not entry.get("target"):
            raise ValueError("evidence entry needs 'id' and 'target'")
        self._entries.append(dict(entry))
        return self._entries[-1]

    def get(self, target: str) -> list[dict]:
        """All prior entries for one audit target."""
        return [e for e in self._entries if e.get("target") == target]

    def all(self) -> list[dict]:
        return list(self._entries)

    def ids(self) -> list[str]:
        """Ids of all stored entries, for the report's prior_evidence_refs."""
        return [e["id"] for e in self._entries if e.get("id")]

    def suppress(self, finding: dict) -> bool:
        """True when this finding id was already recorded (duplicate)."""
        return any(e.get("id") == finding.get("id") for e in self._entries if finding.get("id"))

    def __len__(self) -> int:
        return len(self._entries)
