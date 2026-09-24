# Benchmarks

Offline decision-layer replay: the rule-based mock backend's
`choose()` over fixed page-shapes — no browser, no network, no
paid APIs. Measures repeatability of the decision layer, not
end-to-end browser runs.

The live end-to-end proof is separate: `demos/wikipedia/run.py`
runs a real browser against real Wikipedia (mock backend, offline
decisions) and verifies exact article URL + title + body markers
(latest verified run: 7 steps, 10 decisions, DONE).
The flight demo needs live Google + Laya + text model and is not
part of CI.

Generated 2026-09-23T14:09:32+00:00 · 5 runs x 2 tasks · total wall 1 ms. Raw evidence: `benchmarks.json`.

| task | runs | success rate | steps (median) | backend calls (median) | backend latency ms (median) | wall ms (median) |
| --- | --- | --- | --- | --- | --- | --- |
| wikipedia | 5 | 5/5 (100%) | 3 (range 3-3) | 4 | 0 | 0 |
| flight-shape | 5 | 5/5 (100%) | 3 (range 3-3) | 4 | 0 | 0 |

Columns: steps = actions executed (fill/click/select); backend calls
= `choose()` decisions incl. terminal DONE/BLOCKED; backend latency
= sum of `choose()` latency_ms per run; wall = measured wall time.

Mock `choose()` latency in-process (n=200): p50 0.012 ms, p95 0.012 ms, max 0.015 ms. (Decision layer only — browser
observation + page loads dominate live runs; the live wikipedia demo
above reports 7 steps / 10 decisions end to end.)

Reproduce: `uv run python scripts/bench_mock.py --runs 5` then
`uv run pytest` (offline gates).
