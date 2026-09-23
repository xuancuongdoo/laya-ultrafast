# laya-ultrafast ⚡

**A browser agent with a dynamic, indexed action space — powered by a local
decision model instead of a cloud API.**

Inspired by [browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast):
same loop, same questions, same validation — but the Jev API call is swapped
for **[Laya](https://brainfunctioncollapse.com/laya)**, running on your own
GPU for $0.

**SGN → KUL on Google Flights in ~6.5 seconds.** One natural-language goal,
actual text generation, and loading waits included.

<a href="docs/demo.mp4"><img src="docs/demo.gif" alt="A real Google Flights search at 1× speed, SGN to KUL, with Laya operation/target decisions" width="100%" /></a>

[Watch the MP4](docs/demo.mp4) · [Read the loop](ultrafast/agent.py)

## The action space

Every observation produces a new element table:

```text
[1] combobox  Where from?        · Ho Chi Minh City
[2] combobox  Where to?          · empty
[3] textbox   Departure          · empty
[4] button    Search flights
...
```

The operations are `CLICK`, `TYPE_TEXT`, `SELECT`, `DONE`, and `BLOCKED`.
Only supported operations and targets are offered.

```text
                      one Laya request (:8770)
                     ┌───────────────────────────┐
page → element table → operation                 │
                     │ click_target              │
                     │ type_text_target          │
                     └─────────────┬─────────────┘
                         use the matching target
                                   │
                    CLICK [4] ─────┤──→ browser
                TYPE_TEXT [2] ─────┘
                          ↓
                   small LLM → text → browser
```

Target questions are speculative. If the operation is `CLICK`, only
`click_target` can execute. Two decisions, **one local round trip**
(~100–190ms, $0). Laya needs ≥2 options per choice, so single-candidate
heads get a `[0] none of the above` pad stripped before validation.

**Shortlist → batch → rerank.** Laya degrades past ~10 options per choice
(measured 0.46/0.21/0.20/0.14 on 4 similar links), so big pages never reach
it whole: code pre-filters to ≤10 per batch (`shortlist()`), batch winners
advance, one final rerank over the top-3. See
[model.py](backends/laya/model.py).

There are no site-specific action scripts or prepared field strings in the
policy. The flight demo supplies a goal and independently verifies the
outcome.

## Try it

```bash
git clone https://github.com/xuancuongdoo/laya-ultrafast.git
cd laya-ultrafast
uv sync
cp .env.example .env
# Laya needs no key. Add TEXT_MODEL_API_KEY for field text only.
uv run ultrafast
```

Open **http://127.0.0.1:8766** and enter a goal. **Choose + act** pauses
before execution. First, start Laya itself (weights download once, stay local):

```bash
uv pip install laya
python -m laya serve --port 8770
```

`TEXT_MODEL_API_KEY` is any OpenAI-compatible key. Decisions never touch it —
only field text does.

## Use the library

```python
from ultrafast import Agent

with Agent(
    "https://www.google.com/travel/flights?hl=en",
    "One-way flight Ho Chi Minh City to Kuala Lumpur, 1 adult economy. "
    "Stop when matching flight options are visible.",
) as agent:
    for state in agent.run():
        print(state["elapsed_ms"], state["status"])
```

Run with `uv run --env-file .env python your_script.py`. The same policy can
run a different task — see [demos/flight-search](demos/flight-search).

## Why it moves

- **One request per decision cycle.** Operation and target heads share the
  same observed state.
- **No screenshots in the default agent loop.** Laya consumes structured
  state. The inspector opts into screenshots; the video uses a separate
  continuous screencast.
- **One browser call per snapshot.** Read visible controls, their names,
  values, and text atomically. Keep references to the actual DOM nodes.
- **Validate the selected target.** Clicks check the document, form values,
  target, and nearby context. Resolve current geometry and reject covered
  controls before input.
- **Wait for useful state.** After typing into a combobox, wait for visible
  suggestions, capped at 200 ms. Other interactions get at most two animation
  frames or 50 ms. These reads happen after execution is logged.
- **Batch big menus.** Never send more than 10 options in one choice —
  shortlist in code, rerank the survivors.

Every executed target is resolved from an observed node. The executor
rechecks page freshness and click occlusion. Model output never becomes
selectors, coordinates, shell commands, or executable JavaScript.
Text-helper output must parse as a small JSON object before typing.

## Small enough to read

| File | Job |
| --- | --- |
| [agent.py](ultrafast/agent.py) | The complete loop and text-helper handoff |
| [snapshot.js](ultrafast/snapshot.js) | Atomic DOM snapshot, indexed controls, freshness guards |
| [browser.py](ultrafast/browser.py) | Browser connection, current geometry, execution |
| [model.py](backends/laya/model.py) | Dynamic operation/target heads, batch+rerank, text generation |
| [questions.py](ultrafast/questions.py) | Model instructions |
| [demo.py](ultrafast/demo.py) | Local inspector |

Swap `backends/laya` for another decision backend without touching the loop —
`choose(state, goal, history)` is the only contract.

## Evidence and limits

The current video is a **~6.5 s** Google Flights run (SGN → KUL, one-way,
1 adult, economy). Timing includes model calls, generated text, browser
work, and loading waits. A fresh independent check verifies the one-way
setting, SGN, KUL, Oct 7, and visible flight options (AirAsia nonstop
₫1,653,781). The video plays at 1×.

Honest limits, all measured: Laya's operation head bails to DONE on big
pages and TYPE_TEXT never wins on its own — so the harness routes the
operation in code and asks Laya *which* target. Options per choice cap at
~10 (Jev takes 255). Laya shines as guard / judge / router, not as a
drop-in click-picker. See [Proof vs jev-ultrafast](#proof-vs-jev-ultrafast).

A `DONE` choice still requires independent outcome verification. The DOM
reader handles common HTML and ARIA controls, not the full accessible-name
specification. Shadow roots, frames, canvas, uploads, pop-up tabs, nested
scrolling, and arbitrary keyboard widgets remain outside this MVP.

## Proof vs jev-ultrafast

|  | jev-ultrafast | laya-ultrafast |
|---|---|---|
| Decision model | Jev API (cloud, $) | Laya :8770 (local, $0) |
| Decision latency | ~143–164ms median | ~100–190ms measured |
| Options per choice | up to 255 | ≤10 (batched + reranked) |
| Operation head | reliable | weak — code forces op, Laya picks target |
| Text | mercury-2.5 | any OpenAI-compatible small model |

## Development

```bash
uv run ruff check .
uv run pytest
node --check ultrafast/snapshot.js
uv build
```

Tests are offline. Credentials and raw traces stay ignored.

---

[Browser Use](https://github.com/browser-use/browser-use) · [Browser Harness](https://github.com/browser-use/browser-harness) · [Laya](https://brainfunctioncollapse.com/laya) · Inspired by [browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast)
