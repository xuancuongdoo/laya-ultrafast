# OSS plan — laya-ultrafast vs upstream surface

Sources: `browser-use/jev-ultrafast` README + tree via GitHub API (2026-09-23);
`browser-use/browser-use` repo tree (`.github/`, workflows, issue templates)
and README community/docs links; local repo tree + git log.

## 1. What upstream has that we lack

| Surface | jev-ultrafast | browser-use (main) | laya-ultrafast (now) |
|---|---|---|---|
| README proof | banner.svg, demo.gif+mp4 @1x, evidence+limits section | badges (docs, discord), benchmark chart | demo.gif+mp4, vs-table — no banner, no badges |
| Measurements | `docs/performance.md` + JSON (flights-measurement, full-speed) | separate `browser-use/benchmark` repo | none — README claims ~6.5 s / 100–190 ms unsourced |
| API/library docs | README "Use the library" + readable-code table (agent/browser/model/questions/demo) | hosted docs (docs.browser-use.com, separate docs repo) + llms.txt | backend-contract snippet only |
| Inspector/demo UI | `demo.py` local inspector (:8766, Start demo, Choose-next, probs) | CLI + cloud | `ultrafast/demo.py` exists — undocumented in README |
| CI | none (no .github at all) | lint.yml, test.yaml, install-script, stale-bot, eval-on-pr | none |
| Contributing | none (AGENTS.md only) | `.github/CONTRIBUTING.md` + SECURITY.md | AGENTS.md only |
| Issue templates | none | 4 forms (element bug, bug, feature, docs) + config.yml | none |
| Community | none (links up to browser-use Discord/docs) | Discord, Discussions-equivalent, cloud waitlist CTA | none |
| Scripts | check_guards, measure/record/render_flights, smoke | extensive scripts/ | none |

## 2. Recommendations

**Docs host: mkdocs-material + mkdocstrings, on GitHub Pages.** Rationale:
repo is small and code-first like upstream — hosted docs should be thin
(quickstart, backend contract, measurements, FAQ) with API pages generated
from docstrings, not hand-maintained. Plain docstrings-only leaves no landing
page for badges/SEO; a separate Mintlify-style docs repo is overkill at this size.
Keep the "small enough to read" file table in README as the primary map.

**Issue templates:** copy main-repo shape, trimmed to 3 forms —
`1_bug_report.yml` (goal, expected/actual, trace excerpt, versions),
`2_backend_question.yml` (custom backend contract issues),
`3_docs_issue.yml` — plus `config.yml` pointing to Discussions.
Skip element-detection form until the DOM reader grows.

**Community surface (in order):** (1) GitHub Discussions (one click, no moderation
burden); (2) Discord only after ≥2 external contributors; (3) benchmark table
in README once ≥3 repeated measurements exist — never single-run claims.
Add `llms.txt`-style short pointer only if hosted docs ship.

**CI (minimal, offline-safe):** one workflow — `ruff check`, `pytest`,
`node --check snapshot.js`. No browser/model jobs (matches upstream "tests are
offline"; live scripts stay manual).

**Good first issues (seed 4):** banner.svg; `docs/performance.md` + measurement
JSON from 3 repeated flight runs; document `ultrafast/demo.py` inspector in
README; second demo (Wikipedia article, mirrors upstream `examples/run.py`).

## 3. Sequencing

1. ROADMAP.md (this plan's milestones) — now.
2. CI workflow + CONTRIBUTING.md + 3 issue templates — next, cheap.
3. `scripts/measure_flights.py` port → `docs/performance.md` — before any launch post cites numbers.
4. mkdocs-material skeleton + Pages — with (3).
5. Discussions on; Discord deferred.
