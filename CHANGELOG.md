# Changelog

All notable changes to laya-ultrafast. Format follows Keep a Changelog;
versions follow SemVer.

## [Unreleased]

- Publish prep: `ultrafast.__version__ = "0.1.0"` (mirrors
  `pyproject.toml`), pinned `browser-harness` / `laya` floors,
  `scripts/bench_mock.py` (offline 5 runs x 2 tasks →
  `docs/benchmarks.md` + `benchmarks.json`), `docs/publish.md`
  runbook (`twine check` pass, TestPyPI dry-run 403-on-dummy-token).
- CI (`ruff check`, `ruff format --check`, `pytest`) on push/PR.
- `CONTRIBUTING.md`: demo layout, `choose()` backend contract, gates.
- `backends/mock`: rule-based offline backend implementing the full
  `choose()` / `field_context()` / `field_text()` contract with no network.
- `demos/wikipedia`: second demo (Wikipedia article search) proving the
  backend contract; runs on mock (default, offline) or `--laya`.
- Fix `ultrafast/snapshot.js` cache namespace (`__jevFast` →
  `__ultrafast`): `fresh()`/`act()` never matched, so every demo action
  raised `StalePage`.

## [0.1.0] — 2026-09-23

- Local-decision browser agent (port of browser-use/jev-ultrafast to Laya).
- One Laya round trip per cycle (~100–190 ms) picks operation + target on `:8770`;
  a small OpenAI-compatible model fills field text only.
- Indexed element table per snapshot; code routes the operation, Laya picks the target.
- Shortlist → batch (≤10) → rerank top-3 for big pages.
- `backends/laya/model.py` with swappable backend contract (`choose()`); backend
  injectable via `Agent(..., backend=...)`.
- Flight-search demo (SGN → KUL, ~6.5 s) with `docs/demo.mp4` / `docs/demo.gif`.
- Offline tests (batching + validation, no model calls); MIT license.
