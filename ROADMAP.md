# ROADMAP — laya-ultrafast

## Where we are (v0.1.0, MVP)

Local-decision browser agent: Laya picks operation+target on :8770, small
OpenAI-compatible model fills field text only. One demo (SGN→KUL flight search),
offline tests, MIT license. Full comparison: [docs/oss-plan.md](docs/oss-plan.md).

## v0.2 — OSS hygiene (next)

- [x] CI: ruff + pytest + `node --check snapshot.js` (offline, one workflow)
- [x] CONTRIBUTING.md + SECURITY.md (short, mirror browser-use shape)
- [x] 3 issue templates: bug report, backend question, docs issue
- [ ] Enable GitHub Discussions; Discord deferred until ≥2 external contributors
- [ ] `banner.svg` + README badges (CI, license)

## v0.3 — Evidence before claims

- [ ] Port `scripts/measure_flights.py`: 3+ repeated runs → measurement JSON
- [ ] `docs/performance.md`: matched table (median, budgets, verification results)
- [ ] Qualify or source every README number against performance.md
- [x] Second demo (Wikipedia article run, mirrors upstream `examples/run.py`)

## v0.4 — Hosted docs

- [ ] mkdocs-material + mkdocstrings on GitHub Pages (thin: quickstart,
      backend contract, measurements, FAQ; API from docstrings)
- [ ] Document `ultrafast/demo.py` inspector in README + docs
- [ ] Good-first-issue seed set (see oss-plan §2)

## Later / out of scope for MVP

- DOM reader beyond common HTML/ARIA (shadow roots, frames, canvas, uploads,
  pop-up tabs, nested scrolling) — tracked, not scheduled
- Operation-head recovery (Laya bails to DONE on big pages; harness routes op
  in code) — needs upstream model work, not harness workarounds
- Discord server, benchmark repo, hosted/cloud offering — only on real demand

## Non-goals (standing)

Site-specific plans or hardcoded field values; model-emitted selectors/code;
committing credentials or traces; single-run performance claims.
