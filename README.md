# laya-ultrafast ⚡

A browser agent with a dynamic, indexed action space — one goal in,
typed operation + element decisions out. A port of
[browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast)
with the Jev API swapped for **[Laya](https://brainfunctioncollapse.com/laya)**,
a local decision model that runs on your own GPU for $0.

![demo](assets/demo.mp4)

## How it works

```
goal ("one-way SGN → KUL")
  → snapshot.js reads the DOM as a table (no screenshots, no vision model)
  → Laya picks operation + target in one round trip (~100–190ms, $0)
  → small LLM writes field text only (never picks actions)
  → browser.py validates at commit (freshness, geometry, occlusion)
  → Choose. Act. Repeat.
```

**Shortlist → batch → rerank.** Laya degrades past ~10 options per choice
(measured 0.46/0.21/0.20/0.14 on 4 similar links), so big pages never reach
it whole: code pre-filters to ≤10 per batch, batch winners advance, one
final rerank over the top-3. See `shortlist()` + `choose()` in `laya_model.py`.

Laya needs ≥2 options per choice, so single-candidate heads get a `[0] none
of the above` pad that is stripped before validation (never executable).

## Setup (model stays local — we ship setup, not weights)

```bash
pip install laya                    # decision model
python -m laya serve --port 8770    # local classifier (2.3 GB weights, first run downloads)
pip install -r requirements.txt
export TEXT_MODEL_API_KEY=...       # any OpenAI-compatible key, for field text only
export LAYA_URL=http://127.0.0.1:8770/api/predict   # default

python examples/flight_search.py    # SGN → KUL end-to-end
```

## vs jev-ultrafast

|  | jev-ultrafast | laya-ultrafast |
|---|---|---|
| Decision model | Jev API (cloud, $) | Laya :8770 (local, $0) |
| Decision latency | ~143–164ms median | ~100–190ms measured |
| Options per choice | up to 255 | ≤10 (batched + reranked) |
| Operation head | reliable | weak — code forces op, Laya picks target |
| Text | mercury-2.5 | any OpenAI-compatible small model |

Honest limits (all measured, see video): the operation head bails to DONE
on big pages and TYPE_TEXT never wins on its own — so the harness routes the
operation in code and asks Laya *which* target. Laya shines as guard / judge /
router, not as a drop-in click-picker. The proof video shows both sides.

## Files

| File | Job |
|---|---|
| `laya_model.py` | `choose()` (shortlist→batch→rerank), `field_text()`, validation |
| `laya_agent.py` | observe–decide–act loop with budgets |
| `laya_browser.py` | CDP browser, commit-time validation |
| `snapshot.js` | atomic DOM snapshot (unchanged from upstream) |
| `questions.py` | `NEXT_ACTION` / `TARGET` / `TEXT_VALUE` prompt pack |
| `examples/flight_search.py` | the SGN→KUL demo from the video |
