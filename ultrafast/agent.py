"""The complete agent loop. Typed choices, observable state, bounded execution."""

import base64
import time
from pathlib import Path
from typing import Any

from ultrafast.browser import Browser, StalePage
from ultrafast.models import (
    ActionSpace,
    AgentSnapshot,
    AgentState,
    Decision,
    FieldContext,
    HistoryEntry,
    PageObservation,
)
from ultrafast.questions import MAX_STEPS


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _as_action_dict(action: Any) -> dict:
    if isinstance(action, dict):
        return action
    return action.to_dict() if hasattr(action, "to_dict") else dict(action)


class Agent:
    def __init__(self, url, goals, *, record_dir=None, screenshots=False, backend=None):
        import importlib

        self.backend = importlib.import_module(backend or "backends.laya.model")
        task = goals.strip() if isinstance(goals, str) else "\n".join(goals).strip()
        if not task:
            raise ValueError("Supply a task")
        plan = [task]
        self.pending_text = None
        self.browser = Browser(url)
        self.record_dir = Path(record_dir) if record_dir else None
        self.screenshots = screenshots or bool(record_dir)
        try:
            page = self.browser.observe(screenshot=self.screenshots)
        except Exception:
            self.browser.close()
            raise
        if not isinstance(page, PageObservation):
            page = PageObservation.from_dict(page)
        self.state = AgentState(
            browser=self.browser,
            goal="\n".join(plan),
            page=page,
            decision=None,
            history=[],
            status="ready",
            plan=plan,
            plan_index=0,
            decisions=[],
            text_calls=[],
            elapsed_ms=0,
            started_at=None,
            record=bool(self.record_dir),
        )
        if self.record_dir:
            self.record_dir.mkdir(parents=True, exist_ok=True)
            (self.record_dir / "000000.jpg").write_bytes(base64.b64decode(page.screenshot))

    def snapshot(self) -> AgentSnapshot:
        state = self.state
        page = state.page if isinstance(state.page, PageObservation) else PageObservation.from_dict(state.page)
        space = self.backend.action_space([_as_action_dict(a) for a in page.actions])
        elements = space[0] if isinstance(space, ActionSpace) else space.elements
        el_dicts = [e.to_dict() if hasattr(e, "to_dict") else dict(e) for e in elements]
        decisions = [d.to_dict() if hasattr(d, "to_dict") else dict(d) for d in (state.decisions or [])]
        history = [h.to_dict() if hasattr(h, "to_dict") else dict(h) for h in (state.history or [])]
        decision = state.decision
        if decision is not None and hasattr(decision, "to_dict"):
            decision = decision.to_dict()
        return AgentSnapshot(
            status=state.status,
            goal=state.goal,
            page=page.to_dict(),
            decision=decision,
            history=history,
            plan=list(state.plan),
            plan_index=state.plan_index,
            decisions=decisions,
            text_calls=list(state.text_calls),
            elapsed_ms=state.elapsed_ms,
            started_at=state.started_at,
            record=state.record,
            elements=el_dicts,
        )

    def command(self, name, body=None):
        body = body or {}
        state = self.state
        page = state.page if isinstance(state.page, PageObservation) else PageObservation.from_dict(state.page)
        state.page = page
        if name == "tick":
            try:
                self.command("predict", {})
                return self.command("act", {"fingerprint": state.page.fingerprint})
            except StalePage:
                state.decision = None
                state.status = "ready"
                state.page = state.browser.observe(screenshot=self.screenshots)
                state.elapsed_ms = round((time.perf_counter() - state.started_at) * 1000)
                return self.snapshot()
        elif name == "predict":
            if not state.browser:
                raise ValueError("Start a demo first")
            if state.started_at is None:
                state.started_at = time.perf_counter()
            if not state.browser.fresh(state.page):
                state.page = state.browser.observe(screenshot=self.screenshots)
            state.decision = None
            if state.status in {"done", "blocked"}:
                raise ValueError("This run has stopped. Start a fresh demo.")
            if len(state.decisions) >= MAX_STEPS * 2:
                raise ValueError("Reached the demo's model-call budget")
            history_dicts = [h.to_dict() if hasattr(h, "to_dict") else dict(h) for h in state.history]
            decision = self.backend.choose(state.page.to_dict(), state.goal, history_dicts)
            if not isinstance(decision, Decision):
                decision = Decision.from_dict(decision)
            decision.fingerprint = state.page.fingerprint
            decision.elapsed_ms = round((time.perf_counter() - state.started_at) * 1000)
            state.decision = decision
            state.decisions.append(decision.to_dict())
            state.status = "predicted"
        elif name == "act":
            decision, page = state.decision, state.page
            if isinstance(decision, dict):
                decision = Decision.from_dict(decision)
            fingerprint = body.get("fingerprint")
            if not decision or fingerprint != page.fingerprint:
                raise ValueError("Observe and choose before acting")
            # Consume once, before any mutation or model call. A retry cannot double-click.
            state.decision = None
            selected = decision.choice
            if selected in {"DONE", "BLOCKED"}:
                if not state.browser.fresh(page):
                    state.status = "ready"
                    raise StalePage("Page changed since the decision. Choose again.")
                state.status = "done" if selected == "DONE" else "blocked"
                state.plan_index = int(selected == "DONE")
                state.elapsed_ms = round((time.perf_counter() - state.started_at) * 1000)
                return self.snapshot()
            action = next(a for a in page.actions if _get(a, "id") == selected)
            action_d = _as_action_dict(action)
            if len(state.history) >= MAX_STEPS:
                state.status = "blocked"
                raise ValueError(f"Stopped at the {MAX_STEPS}-action demo budget")
            text, helper = None, None
            if action_d["kind"] == "fill":
                if not state.browser.fresh(page):
                    raise StalePage("Page changed before text generation. Choose again.")
                history_dicts = [h.to_dict() if hasattr(h, "to_dict") else dict(h) for h in state.history]
                context = self.backend.field_context(state.goal, action_d, page.to_dict(), history_dicts)
                if not isinstance(context, FieldContext):
                    context = FieldContext.from_dict(context)
                if self.pending_text and self.pending_text[0].to_dict() == context.to_dict():
                    _, text, helper = self.pending_text
                else:
                    text, helper = self.backend.field_text(context.to_dict())
                    self.pending_text = (context, text, helper)
                    state.text_calls.append({**helper, "field": action_d["label"], "value": text})
            # Browser.act checks freshness immediately before input, including after text generation.
            state.browser.act(action_d, page, text=text)
            self.pending_text = None
            state.elapsed_ms = round((time.perf_counter() - state.started_at) * 1000)
            probabilities = decision.probabilities or {}
            # Record execution before observing. A stale post-action observation must not erase the action.
            entry = HistoryEntry(
                step=len(state.history) + 1,
                action=action_d["label"],
                kind=action_d["kind"],
                choice=selected,
                probability=probabilities.get(selected, 0),
                confidence=decision.confidence,
                latency_ms=decision.latency_ms,
                text=text,
                text_helper=helper["model"] if helper else None,
                text_latency_ms=helper["latency_ms"] if helper else 0,
                operation=decision.operation,
                target=decision.target,
                page_changed=None,
                url=page.url,
                usage=decision.usage,
                executed_ms=round((time.perf_counter() - state.started_at) * 1000),
                elapsed_ms=state.elapsed_ms,
            )
            state.history.append(entry)
            state.page = state.browser.observe(screenshot=self.screenshots)
            state.elapsed_ms = round((time.perf_counter() - state.started_at) * 1000)
            entry.page_changed = state.page.fingerprint != page.fingerprint
            entry.url = state.page.url
            entry.elapsed_ms = state.elapsed_ms
            if state.record:
                (self.record_dir / f"{state.elapsed_ms:06d}.jpg").write_bytes(base64.b64decode(state.page.screenshot))
            repeated = state.history[-3:]
            state.status = (
                "blocked"
                if len(repeated) == 3 and all(h.page_changed is False and h.kind != "wait" for h in repeated)
                else "ready"
            )
        else:
            raise ValueError("Unknown command")
        return self.snapshot()

    def run(self):
        while self.state.status not in {"done", "blocked"}:
            yield self.command("tick")

    def close(self):
        self.browser.close()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()
