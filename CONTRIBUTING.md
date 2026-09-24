# Contributing to laya-ultrafast

Read `README.md` and `AGENTS.md` first. Keep the loop small:
page → indexed elements → operation + target → execution.

## Setup

```bash
git clone https://github.com/xuancuongdoo/laya-ultrafast.git && cd laya-ultrafast
uv sync
uv pip install laya && python -m laya serve --port 8770  # separate terminal, weights download once
cp .env.example .env  # add TEXT_MODEL_API_KEY (field text only, never decisions)
```

## Adding a demo: `demos/<site>/run.py`

Each demo is one natural-language goal against one site. Copy
`demos/flight-search/run.py`:

```python
from ultrafast import Agent

GOAL = "One-way flight Ho Chi Minh City (SGN) to Kuala Lumpur (KUL), ..."

if __name__ == "__main__":
    with Agent("https://www.example.com", GOAL, record_dir="./recordings") as agent:
        for snap in agent.run():
            ...
        print("status:", agent.state["status"])
```

- The goal is the only site-specific input. Do not add site-specific
  plans or hardcoded field values to `ultrafast/` or `backends/`.
- Add a `demos/<site>/README.md` with what it does and how to run it.
- Recordings go to `./recordings/` (gitignored). Keep demo footage at
  its original speed.
- Verify the final outcome independently (page state, not just a
  `DONE` choice): the flight demo checks trip type, SGN, KUL, date,
  and visible options.

## Backend contract: `choose()`

Swap `backends/laya` without touching the loop by injecting another
backend (`Agent(url, goal, backend="backends.<name>.model")`). A backend
module must implement:

```python
action_space(actions) -> (elements, targets, controls)
choose(page, goal, history) -> decision
field_context(goal, action, page, history) -> dict
field_text(context) -> (text, helper)
```

- `choose(page, goal, history)` returns a dict with at least
  `choice` (observed action id, or `DONE`/`BLOCKED`), `operation`,
  `target`, `confidence`, `probabilities`. See `backends/laya/model.py`
  and its use in `ultrafast/agent.py`.
- Targets must resolve from observed DOM nodes and supported operations
  (`CLICK`, `TYPE_TEXT`, `SELECT`, `DONE`, `BLOCKED`). Never emit
  selectors, coordinates, shell, or JavaScript from the model.
- Laya degrades past ~10 options: shortlist → batch (≤10 per batch) →
  rerank top-3. Never send a whole big page in one choice.
- `TYPE_TEXT` invokes the text LLM (`field_text`); cache a stale
  retry's value only while its entire helper input is identical.

## Gates (must hold for every PR)

- Never retry a browser mutation. Log execution before observing its result.
- Screenshots are optional; the model does not consume them.
- Keep credentials server-side (`.env` is ignored). Tests must not call
  paid APIs — `uv run pytest` runs fully offline.
- Verify actual final outcomes independently. A `DONE` choice is not
  proof of success.
- Keep examples, README claims, raw evidence, and model-call counts
  consistent with each other.
- Do not commit or push unless the maintainer requests it.

## Checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

CI (`.github/workflows/ci.yml`) runs the same three commands on every
push to `main` and every pull request.
