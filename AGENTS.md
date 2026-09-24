# laya-ultrafast

Read README.md before editing. Keep the loop small: page → indexed
elements → operation + target → execution.

- The input is one natural-language goal. Do not add site-specific plans
  or hardcoded field values.
- Laya chooses an operation and operation-specific target heads in one
  local request (:8770). Consume only the selected operation's target.
- Targets must map to observed elements and supported operations. Never
  let the model emit selectors or executable code.
- Laya degrades past ~10 options: batch target heads (shortlist → batch
  → rerank top-3). Never send a whole big page in one choice.
- TYPE_TEXT invokes the text LLM. Cache a stale retry's value only while
  its entire helper input is identical.
- Never retry a browser mutation. Log execution before observing its result.
- Screenshots are optional; the model does not consume them. Keep
  demonstration footage at its original speed.
- Keep credentials server-side and .env ignored. Tests must not call paid APIs.
- Verify actual final outcomes independently. A DONE choice is not proof
  of success.
- Keep examples, README claims, raw evidence, and model-call counts consistent.
- No unstructured dicts across module boundaries: define strict typed models
  (dataclasses / pydantic) for states, decisions, results. Dicts stay inside
  a single function only.
- Deep nested hierarchy: group by domain (`ultrafast/`, `backends/<name>/`,
  `demos/<usecase>/`), never flat siblings of unrelated concerns. New domain
  = new folder, not a new top-level file.
- Absolute imports only (`from ultrafast.agent import ...`), never relative
  (`from .agent import`, `from ..x import`). Enforced by ruff (no-relative-imports).
- Clean `__init__.py`: re-export public surface only, no logic, no side
  effects on import, no wildcard imports.
- Do not commit or push unless the user requests it.

Checks: `uv run ruff check .`, `uv run pytest`.
