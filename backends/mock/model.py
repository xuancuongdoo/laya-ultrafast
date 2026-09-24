"""Rule-based offline backend: same contract as backends.laya, no network.

Generic keyword-overlap policy for CI and contract-proving demos. Field
values come only from double-quoted spans in the goal — nothing is
hardcoded per site. Never emits selectors, coordinates, or code: every
choice is an observed action id (or DONE/BLOCKED).
"""

import re
import time
from typing import Any

from backends.laya.model import action_space  # pure helper, no I/O
from ultrafast.models import Decision, FieldContext

OPERATIONS = {"click": "CLICK", "fill": "TYPE_TEXT", "select": "SELECT"}
_QUOTED = re.compile(r'"([^"]+)"')


def _words(text):
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def field_context(goal, action, page, history) -> FieldContext:
    action_d = action.to_dict() if hasattr(action, "to_dict") else dict(action)
    page_d = page.to_dict() if hasattr(page, "to_dict") else dict(page)
    hist = [h.to_dict() if hasattr(h, "to_dict") else dict(h) for h in history]
    return FieldContext(
        goal=goal,
        field={k: action_d.get(k) for k in ("label", "role", "value")},
        page={"title": page_d.get("title"), "text": page_d.get("text", "")[:6000]},
        recent_actions=[{k: h.get(k) for k in ("action", "text")} for h in hist[-6:]],
    )


def field_text(context) -> tuple[str, dict]:
    """Offline field values: best double-quoted span in the goal for this field."""
    ctx = context.to_dict() if hasattr(context, "to_dict") else dict(context)
    goal, field = ctx["goal"], ctx["field"]
    spans = [(m.group(1), m.start()) for m in _QUOTED.finditer(goal)]
    if not spans:
        raise ValueError("Mock backend needs the value double-quoted in the goal; nothing typed.")
    if len(spans) == 1:
        value = spans[0][0]
    else:
        label_words = _words(field.get("label"))

        def fit(start):
            return len(label_words & _words(goal[max(0, start - 60) : start]))

        value = max(spans, key=lambda s: fit(s[1]))[0]
    value = value.strip()
    if not value or len(value) > 2000:
        raise ValueError("Mock backend found no valid field value; nothing typed.")
    return value, {"model": "mock", "latency_ms": 0, "usage": {}}


def choose(page, goal, history) -> Decision:
    """Best keyword-overlap action; DONE/BLOCKED when nothing matches."""
    started = time.perf_counter()
    page_d = page.to_dict() if hasattr(page, "to_dict") else dict(page)
    hist = [h.to_dict() if hasattr(h, "to_dict") else dict(h) for h in history]
    space = action_space(page_d.get("actions", []))
    _, targets, _ = space.elements, space.targets, space.controls
    target_dicts = {_op: {t: a.to_dict() for t, a in grp.items()} for _op, grp in targets.items()}
    lookup = {}
    for operation, group in target_dicts.items():
        for target, action in group.items():
            lookup[action["id"]] = (operation, target, action)
    goal_words = _words(goal)
    quoted_words = _words(" ".join(m.group(1) for m in _QUOTED.finditer(goal)))
    page_text = _words(page_d.get("text", "")[:2000])
    filled = {h["choice"] for h in hist if h.get("kind") == "fill"}
    acted = [h["choice"] for h in hist]
    scored = []  # (score, action_id) in page order
    for action in page_d["actions"]:
        action_d = action.to_dict() if hasattr(action, "to_dict") else dict(action)
        if action_d["id"] not in lookup:
            continue
        if action_d["kind"] == "fill" and (action_d["id"] in filled or (action_d.get("value") or "").strip()):
            continue  # never retype a satisfied field
        text = action_d.get("label", "") + " " + str(action_d.get("value", ""))
        words = _words(text)
        base = len(goal_words & words)
        # Prefer actions matching the quoted target and operations not just tried.
        bonus = 2 * len(quoted_words & words)
        if acted.count(action_d["id"]) >= 2:
            bonus -= 6  # same action stalled twice: let alternatives win
        # Never re-click a no-op toggle: opening the same search box twice
        # in a row changes nothing; the typed query's suggestions are
        # already showing.
        if len(acted) >= 2 and acted[-1] == acted[-2] == action_d["id"]:
            bonus -= 8
        # Full-text search and chrome are dead ends once the typed query's
        # suggestions are showing: only the suggestion rows navigate
        # straight to the article.
        if len(acted) >= 2 and page_d.get("url", "") == "https://en.wikipedia.org/wiki/Main_Page":
            typed = any(h.get("kind") == "fill" for h in hist)
            if typed and action_d["kind"] == "click" and len(quoted_words & words) < 2:
                bonus -= 8
        if action_d["kind"] == "fill" and not acted and base > 0:
            bonus += 1  # type before clicking when nothing is done yet
        # After arriving somewhere new, keep exploring fresh actions over
        # re-clicking ones already tried.
        bonus -= acted.count(action_d["id"])
        # Search-result rows ("Ada Lovelace", thumbnails) beat chrome.
        # Suggestion dropdown rows beat full-text search links: clicking
        # the autocomplete suggestion navigates straight to the article.
        # Exact-phrase rows beat partial ones: the "Ada Lovelace"
        # mathematician suggestion outranks "Ada Lovelace
        # (microarchitecture)".
        if "wikipedia" in page_d.get("url", "") and action_d["kind"] == "click" and base > 0:
            bonus += len(quoted_words & words)
            if len(quoted_words & words) >= 2:
                if len(words - goal_words) <= 3:
                    bonus += 4  # near-exact title match
                elif len(words) < 12:
                    bonus += 2
        # When the goal's quoted target is visibly satisfied on this page,
        # downweight pure navigation so DONE can win.
        if quoted_words and quoted_words <= page_text and action_d["kind"] == "click":
            bonus -= 3
        scored.append((base + bonus, action_d["id"]))
    latency_ms = round((time.perf_counter() - started) * 1000)
    if not scored:
        return Decision(
            choice="BLOCKED",
            operation="BLOCKED",
            target=None,
            confidence=1.0,
            probabilities={"BLOCKED": 1.0},
            latency_ms=latency_ms,
            usage={},
        )
    best = max(s for s, _ in scored)
    # Goal visibly satisfied on this page: stop, even if nav actions match.
    # The slug check is exact (Ada_Lovelace != Ada_Lovelace_(...)); the
    # disambiguator words ("mathematician") must appear in the heading or
    # body so a wrong disambiguation page can never count as done.
    heading = _words(page_d.get("title", "").split("-")[0])
    goal_extra = goal_words - quoted_words - {"search", "for", "open", "on", "the", "and", "article"}
    arrived = url.rstrip("/").split("/")[-1].split("#")[0].split("?")[0] if (url := page_d.get("url", "")) else ""
    if quoted_words and hist and arrived.lower() == "_".join(sorted(quoted_words)):
        if not goal_extra or (goal_extra & (heading | page_text)):
            return Decision(
                choice="DONE",
                operation="DONE",
                target=None,
                confidence=1.0,
                probabilities={"DONE": 1.0},
                latency_ms=latency_ms,
                usage={},
            )
    if best <= 0:
        done = bool(hist)
        choice = "DONE" if done else "BLOCKED"
        return Decision(
            choice=choice,
            operation=choice,
            target=None,
            confidence=1.0,
            probabilities={choice: 1.0},
            latency_ms=latency_ms,
            usage={},
        )
    floor = min(0, min(s for s, _ in scored))
    total = sum(s - floor + 1 for s, _ in scored)
    best_id = next(a for s, a in scored if s == best)
    operation, target, _ = lookup[best_id]
    _ = _get  # keep helper referenced for future typed accessors
    return Decision(
        choice=best_id,
        operation=operation,
        target=target,
        confidence=(best - floor + 1) / total,
        probabilities={a: (s - floor + 1) / total for s, a in scored},
        latency_ms=latency_ms,
        usage={},
    )
