"""Laya makes choices; a small OpenAI-compatible model writes field values.

Port of browser-use/jev-ultrafast model.py: same one-request-per-cycle
shape (operation choice + speculative target heads), but POSTs to the
local Laya classifier (:8770) instead of TypeSafe's API. $0, ~50-200ms.
"""

import json
import math
import os
import time
import urllib.request

from ultrafast.questions import NEXT_ACTION, TARGET, TEXT_VALUE

LAYA_URL = os.environ.get("LAYA_URL", "http://127.0.0.1:8770/api/predict")


def post_json(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def post_text_model(base, key, body):
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                base.rstrip("/") + "/chat/completions",
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception:
            if attempt == 2:
                raise RuntimeError("Model connection failed; no action executed.")
            time.sleep(0.5 * 2**attempt)
    raise RuntimeError("Model unavailable")


def validate_choice(answer, ids):
    try:
        probabilities = answer["probabilities"]
        numbers = [*probabilities.values(), answer["confidence"]]
        valid = (
            answer["choice"] in ids
            and set(probabilities) == set(ids)
            and all(type(n) in (int, float) and math.isfinite(n) and 0 <= n <= 1 for n in numbers)
            and abs(sum(probabilities.values()) - 1) < 0.02
            and probabilities[answer["choice"]] >= max(probabilities.values()) - 1e-6
        )
    except (KeyError, TypeError, ValueError):
        valid = False
    if not valid:
        raise ValueError("Invalid Laya response; no action executed.")
    return answer


def action_space(actions):
    """One index per observed element; each operation has its own valid target choices."""
    elements, indices, targets, controls = [], {}, {}, {}
    operations = {"click": "CLICK", "fill": "TYPE_TEXT", "select": "SELECT"}
    for action in actions:
        kind = action["kind"]
        if kind not in operations:
            controls[action["id"].upper()] = action
            continue
        node = action["node"]
        if node not in indices:
            index = str(len(elements) + 1)
            indices[node] = index
            element = {k: action[k] for k in ("role", "value", "checked", "selected", "expanded") if k in action}
            element.update(index=index, label=action["label"].split(" → ")[0], operations=[])
            if kind == "select":
                element["value"] = action.get("current_value", "")
                element["options"] = []
            elements.append(element)
        index = indices[node]
        operation = operations[kind]
        group = targets.setdefault(operation, {})
        element = elements[int(index) - 1]
        if operation not in element["operations"]:
            element["operations"].append(operation)
        target = index
        if kind == "select":
            target = "%s:%d" % (index, len(element["options"]) + 1)
            element["options"].append({"index": target, "label": action["label"], "value": action["value"]})
        group[target] = action
    return elements, targets, controls


def short_label(label, limit=60):
    label = label or ""
    return label if len(label) <= limit else label[: limit - 1] + "…"


def field_context(goal, action, page, history):
    return {
        "goal": goal,
        "field": {k: action.get(k) for k in ("label", "role", "value")},
        "page": {"title": page["title"], "text": page["text"][:6000]},
        "recent_actions": [{k: h.get(k) for k in ("action", "text")} for h in history[-6:]],
    }


def field_text(context):
    """Text comes from a small OpenAI-compatible model (never Laya, never hardcoded)."""
    key = os.environ.get("TEXT_MODEL_API_KEY")
    if not key:
        raise ValueError("TYPE_TEXT needs TEXT_MODEL_API_KEY; no text is hardcoded or guessed by the executor.")
    base = os.environ.get("TEXT_MODEL_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
    model = os.environ.get("TEXT_MODEL", "x-ai/grok-4-1-fast")
    started = time.perf_counter()
    result = post_text_model(
        base,
        key,
        {
            "model": model,
            "max_tokens": 1024,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": TEXT_VALUE},
                {"role": "user", "content": json.dumps(context)},
            ],
        },
    )
    try:
        output = json.loads(result["choices"][0]["message"]["content"])
        value = output["text"]
        if set(output) != {"text"} or not isinstance(value, str) or not value.strip() or len(value) > 2000:
            raise ValueError()
    except (ValueError, KeyError, TypeError):
        raise ValueError("Text helper returned no valid field value; nothing typed.") from None
    return value, {
        "model": model,
        "latency_ms": round((time.perf_counter() - started) * 1000),
        "usage": result.get("usage", {}),
    }


def shortlist(candidates, goal, per_batch=10):
    """Code pre-filter: rank candidates by keyword overlap with goal, chunk into <=10."""
    words = set(goal.lower().split())

    def score(a):
        text = (a.get("label", "") + " " + str(a.get("value", ""))).lower()
        return len(words & set(text.split()))

    ranked = sorted(candidates.items(), key=lambda kv: score(kv[1]), reverse=True)
    return [dict(ranked[i : i + per_batch]) for i in range(0, len(ranked), per_batch)]


def _ask(question_id, criteria, instructions, state_obj):
    body = {
        "state": state_obj,
        "questions": {question_id: {"type": "choice", "criteria": criteria, "instructions": instructions}},
    }
    return post_json(LAYA_URL, body)["answers"][question_id]


def choose(state, goal, history, per_batch=10, rerank_k=3):
    """Shortlist -> batch (<=10) -> rerank top-3. Returns same shape as before."""
    import time as _t

    started = _t.perf_counter()
    elements, targets, controls = action_space(state["actions"])
    labels = {
        "CLICK": "Click an element, button, menu option, autocomplete suggestion, or calendar day.",
        "TYPE_TEXT": "Enter or replace text in an editable field. A small LLM will supply the value from the goal.",
        "SELECT": "Select an observed dropdown value.",
    }
    operations = {key: labels[key] for key in targets}
    operations.update({key: value["label"] for key, value in controls.items()})
    operations.update(DONE="Every requirement is visibly satisfied.", BLOCKED="No supported operation can progress.")
    state_obj = {
        "page": {k: state[k] for k in ("url", "title", "text") if k in state},
        "recent_actions": [{k: h.get(k) for k in ("action", "kind", "text", "page_changed")} for h in history[-10:]],
    }
    # 1. operation head (small menu, Laya is fine here)
    op_a = _ask("operation", operations, "Goal: %s. Rules: %s" % (goal, NEXT_ACTION), state_obj)
    operation_answer = validate_choice({**op_a, "probabilities": dict(op_a["probabilities"])}, operations)
    operation = operation_answer["choice"]
    if operation not in targets:
        choice = controls[operation]["id"] if operation in controls else operation
        return {
            "choice": choice,
            "operation": operation,
            "target": None,
            "confidence": operation_answer["confidence"],
            "probabilities": {choice: operation_answer["probabilities"][operation]},
            "operation_probabilities": operation_answer["probabilities"],
            "target_probabilities": {},
            "target_confidence": None,
            "raw_answers": {"operation": op_a},
            "model": op_a.get("model"),
            "usage": {},
            "latency_ms": round((_t.perf_counter() - started) * 1000),
            "request": None,
            "debug": {"batches": 0, "reranked": 0},
        }
    # 2. batch target heads (<=10 each), keep winners
    cands = targets[operation]
    batches = shortlist(cands, goal, per_batch)
    winners = []  # (index, prob)
    batch_answers = []
    for b in batches:
        crit = {i: "[%s] %s" % (i, short_label(a["label"])) for i, a in b.items()}
        if len(crit) == 1:
            crit["0"] = "[0] none of the above"
        ans = _ask(
            operation.lower() + "_target",
            crit,
            "Goal: %s. Pick the best target for %s. %s" % (goal, operation, TARGET),
            state_obj,
        )
        probs = {k: v for k, v in ans["probabilities"].items() if k != "0"}
        batch_answers.append(ans)
        if probs:
            best = max(probs, key=probs.get)
            winners.append((best, probs[best]))
    if not winners:
        raise ValueError("No valid target for %s; no action executed." % operation)
    # 3. rerank top-k survivors in one final call
    winners.sort(key=lambda w: w[1], reverse=True)
    final = {i: "[%s] %s" % (i, short_label(cands[i]["label"])) for i, _ in winners[:rerank_k]}
    if len(final) == 1:
        target = next(iter(final))
        tconf = winners[0][1]
        tprobs = {target: 1.0}
    else:
        ans = _ask(
            operation.lower() + "_rerank",
            final,
            "Goal: %s. Final pick for %s among shortlisted best. %s" % (goal, operation, TARGET),
            state_obj,
        )
        target_answer = validate_choice({**ans, "probabilities": dict(ans["probabilities"])}, final)
        target = target_answer["choice"]
        tconf = target_answer["confidence"]
        tprobs = target_answer["probabilities"]
    choice = cands[target]["id"]
    return {
        "choice": choice,
        "operation": operation,
        "target": target,
        "confidence": operation_answer["confidence"],
        "probabilities": {cands[i]["id"]: (tprobs.get(i, 0)) for i in final},
        "operation_probabilities": operation_answer["probabilities"],
        "target_probabilities": tprobs,
        "target_confidence": tconf,
        "raw_answers": {"operation": op_a, "batches": len(batches)},
        "model": op_a.get("model"),
        "usage": {},
        "latency_ms": round((_t.perf_counter() - started) * 1000),
        "request": None,
        "debug": {"batches": len(batches), "reranked": len(final)},
    }
