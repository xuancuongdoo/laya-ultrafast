"""Credential-exposure surface: PATHS ONLY, never file contents or values.

Flags a root .env (info if gitignored, high if tracked), suspicious
filenames (medium), and *.pem/*.key files (high). Pure stdlib + git CLI.
Vendor/skip dirs mirror the recon map so third-party files never flag.
"""

from __future__ import annotations

import fnmatch
import os
import subprocess
from pathlib import Path

SKIP_DIRS = frozenset({".venv", "__pycache__", ".git", "node_modules", "dist", "recordings"})
NAME_PATTERNS = ("*secret*", "*token*", "*credential*", "*private*key*")


def _finding(target: str, fid: str, severity: str, detail: str) -> dict:
    # area mirrors target: chain.verify_finding requires area, audit shape wants target.
    return {"id": fid, "target": target, "area": target, "severity": severity, "detail": detail}


def _gitignore_match(root: Path, rel: str) -> bool:
    """Best-effort .gitignore check for rel (last matching pattern wins)."""
    try:
        lines = (root / ".gitignore").read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return False
    ignored = False
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        negated = line.startswith("!")
        pattern = line[1:] if negated else line
        pattern = pattern.strip().lstrip("/")
        if not pattern:
            continue
        candidates = (rel, rel.rsplit("/", 1)[-1])
        if any(fnmatch.fnmatchcase(c, pattern) for c in candidates):
            ignored = not negated
    return ignored


def _is_ignored(root: Path, rel: str) -> bool:
    """True when git treats rel as ignored; .gitignore fallback outside a repo."""
    try:
        proc = subprocess.run(
            ["git", "check-ignore", "-q", rel],
            cwd=root,
            capture_output=True,
            timeout=30,
        )
    except OSError:
        return _gitignore_match(root, rel)
    if proc.returncode == 0:
        return True
    if proc.returncode == 1:
        return False
    return _gitignore_match(root, rel)


def _walk_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            yield Path(dirpath) / name


def run(target_root) -> list[dict]:
    """Audit target_root for credential-exposure paths. Never reads file contents."""
    root = Path(target_root)
    target = str(target_root)
    findings: list[dict] = []
    if (root / ".env").is_file():
        if _is_ignored(root, ".env"):
            findings.append(_finding(target, "SEC-DOTENV-1", "info", ".env present at repo root (gitignored)"))
        else:
            findings.append(_finding(target, "SEC-DOTENV-1", "high", ".env present at repo root (tracked by git)"))
    names = keys = 0
    for file in _walk_files(root):
        lower = file.name.lower()
        rel = file.relative_to(root).as_posix()
        if lower.endswith((".pem", ".key")):
            keys += 1
            findings.append(_finding(target, f"SEC-KEY-{keys}", "high", f"{rel}: private key material by extension"))
        elif any(fnmatch.fnmatchcase(lower, pat) for pat in NAME_PATTERNS):
            names += 1
            findings.append(_finding(target, f"SEC-NAME-{names}", "medium", f"{rel}: credential-like filename"))
    return findings


__all__ = ["NAME_PATTERNS", "SKIP_DIRS", "run"]
