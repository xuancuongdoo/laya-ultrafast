"""Coverage Ledger: which (area, phase) pairs are covered.

Phases mirror the audit diagram: recon -> hunt -> verify -> report.
Status per cell: pending | covered | verified.
Areas are audit scopes (e.g. "auth", "ultrafast/agent.py"); the report's
area list and coverage fraction both derive from this ledger.
"""

from __future__ import annotations

import json
from pathlib import Path

PHASES = ("recon", "hunt", "verify", "report")
STATUSES = ("pending", "covered", "verified")
COVERED = {"covered", "verified"}


class CoverageLedger:
    def __init__(self) -> None:
        self._cells: dict[tuple[str, str], str] = {}

    def mark(self, area: str, phase: str, status: str = "covered") -> str:
        if phase not in PHASES:
            raise ValueError(f"unknown phase {phase!r}, expected one of {PHASES}")
        if status not in STATUSES:
            raise ValueError(f"unknown status {status!r}, expected one of {STATUSES}")
        if not area:
            raise ValueError("area must be non-empty")
        self._cells[(area, phase)] = status
        return status

    def status(self, area: str, phase: str) -> str:
        return self._cells.get((area, phase), "pending")

    def areas(self, area: str | None = None) -> list[str]:
        """Areas touched so far — the report's area list (or [area] fallback)."""
        touched = sorted({a for (a, _) in self._cells})
        if area is not None:
            return touched or [area]
        return touched

    def uncovered(self, area: str | None = None) -> list[tuple[str, str]]:
        areas = [area] if area else self.areas()
        return [(a, p) for a in areas for p in PHASES if self.status(a, p) not in COVERED]

    def coverage(self, area: str | None = None) -> float:
        areas = [area] if area else self.areas()
        total = len(areas) * len(PHASES)
        if not total:
            return 0.0
        done = sum(1 for a in areas for p in PHASES if self.status(a, p) in COVERED)
        return done / total

    def validate(self) -> bool:
        for (area, phase), status in self._cells.items():
            if phase not in PHASES:
                raise ValueError(f"unknown phase {phase!r} for {area!r}")
            if status not in STATUSES:
                raise ValueError(f"unknown status {status!r} for {(area, phase)!r}")
            if not area:
                raise ValueError("ledger holds an empty area")
        return True

    def to_dict(self) -> dict:
        return {f"{a}::{p}": s for (a, p), s in sorted(self._cells.items())}

    @classmethod
    def from_dict(cls, raw: dict) -> CoverageLedger:
        ledger = cls()
        for key, status in raw.items():
            area, _, phase = key.partition("::")
            ledger.mark(area, phase, status)
        return ledger

    def save(self, path: str | Path) -> Path:
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(self.to_dict(), indent=2))
        return dest

    @classmethod
    def load(cls, path: str | Path) -> CoverageLedger:
        return cls.from_dict(json.loads(Path(path).read_text()))
