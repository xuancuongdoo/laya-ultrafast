# laya-ultrafast ⚡

Browser agent with a dynamic, indexed action space — local [Laya](https://brainfunctioncollapse.com/laya) decisions, $0 per run.

SGN → KUL on Google Flights in ~6.5 seconds, text generation and loading waits included.

## Demos

| Demo | What |
| --- | --- |
| [Flight search](demos/flight-search/run.py) | SGN → KUL one-way, 1 adult economy, earliest date (~6.5 s) |

<a href="docs/demo.mp4"><img src="docs/demo.gif" alt="Google Flights search at 1× speed, SGN to KUL" width="100%" /></a>

[Watch the MP4](docs/demo.mp4)

## Quickstart

```bash
git clone https://github.com/xuancuongdoo/laya-ultrafast.git && cd laya-ultrafast
uv sync
uv pip install laya && python -m laya serve --port 8770 # separate terminal, weights download once
cp .env.example .env # add TEXT_MODEL_API_KEY (field text only, never decisions)
uv run python demos/flight-search/run.py
```

## How it works

- Each snapshot builds a fresh indexed element table (`[1] combobox Where from? …`); only supported ops (`CLICK`, `TYPE_TEXT`, `SELECT`, `DONE`, `BLOCKED`) are offered.
- One Laya round trip per cycle (~100–190 ms) picks operation + target on `:8770`; a small OpenAI-compatible model fills field text only.
- Big pages never reach Laya whole: code shortlists to ≤10 options per batch, batch winners advance, one final rerank over the top-3.
- Every target resolves from an observed DOM node — model output never becomes selectors, coordinates, shell, or JavaScript.

## Backend contract

Swap `backends/laya` without touching the loop — [model.py](backends/laya/model.py) implements one function:

```python
choose(state, goal, history)  # -> operation + target; see ultrafast/agent.py
```

## laya-ultrafast vs jev-ultrafast

| | jev-ultrafast | laya-ultrafast |
| --- | --- | --- |
| Decision model | Jev API (cloud, $) | Laya :8770 (local, $0) |
| Decision latency | ~143–164 ms median | ~100–190 ms measured |
| Options per choice | up to 255 | ≤10 (batched + reranked) |
| Operation head | reliable | weak — code routes op, Laya picks target |
| Field text | mercury-2.5 | any OpenAI-compatible small model |

## Limits

- Laya's operation head bails to DONE on big pages and `TYPE_TEXT` never wins alone — the harness routes the operation in code and asks Laya *which* target.
- `DONE` still requires independent outcome verification; the flight demo checks trip type, SGN, KUL, date, and visible options.
- DOM reader covers common HTML/ARIA controls only — shadow roots, frames, canvas, uploads, pop-up tabs, and nested scrolling are out of scope for this MVP.

Inspired by [browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast).
