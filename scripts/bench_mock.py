"""Repeatable offline benchmark: mock backend over recorded page-shapes.

Runs two tasks N times through the rule-based mock backend's choose() —
pure function calls, no browser, no network, no paid APIs:

- wikipedia: page-shapes replayed from the live mock demo flow
  (search page -> suggestion click -> article -> DONE).
- flight-shape: a synthetic Google-Flights-shaped page (trip-type
  select, destination fill, date grid, search click, results DONE)
  exercising select/fill/click/DONE under the same contract.

Records per run: success, steps (choose calls), backend calls
(decisions), wall time. Writes docs/benchmarks.md (table) and
docs/benchmarks.json (machine-readable raw evidence).

The wikipedia live run (real browser, real Wikipedia) is verified
separately via demos/wikipedia/run.py — this script measures the
decision-layer repeatability offline.
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from backends.mock import model as mock

WIKI_GOAL = 'On Wikipedia, search for "Ada Lovelace" and open the Ada Lovelace mathematician article.'

FLIGHT_GOAL = (
    "One-way flight Ho Chi Minh City (SGN) to Kuala Lumpur (KUL), "
    '1 adult economy. Set trip type "One way", type destination "KUL", '
    "pick the earliest departure date, click Search, stop when results load."
)


def wiki_pages():
    search = {
        "url": "https://en.wikipedia.org/wiki/Main_Page",
        "title": "Wikipedia, the free encyclopedia",
        "text": "Welcome to Wikipedia Search Wikipedia article suggestions mathematics computing",
        "actions": [
            {"id": "e1", "kind": "fill", "label": "Search Wikipedia", "node": 1, "value": ""},
            {"id": "e2", "kind": "click", "label": "Search full text", "node": 2},
            {"id": "e5", "kind": "click", "label": "Donate now", "node": 5},
        ],
    }
    suggest = {
        "url": "https://en.wikipedia.org/w/index.php?search=Ada+Lovelace",
        "title": "Search results - Wikipedia",
        "text": "Search results for Ada Lovelace mathematician Analytical Engine Charles Babbage",
        "actions": [
            {"id": "s1", "kind": "click", "label": "Ada Lovelace", "node": 11},
            {"id": "s2", "kind": "click", "label": "Ada Lovelace (microarchitecture)", "node": 12},
            {"id": "s3", "kind": "click", "label": "Search full text for Ada Lovelace", "node": 13},
        ],
    }
    article = {
        "url": "https://en.wikipedia.org/wiki/Ada_Lovelace",
        "title": "Ada Lovelace - Wikipedia",
        "text": "Ada Lovelace English mathematician Analytical Engine Charles Babbage Lord Byron",
        "actions": [
            {"id": "a1", "kind": "click", "label": "Analytical Engine", "node": 21},
            {"id": "a2", "kind": "click", "label": "Charles Babbage", "node": 22},
            {"id": "a3", "kind": "click", "label": "Main page", "node": 23},
        ],
    }
    return [search, suggest, article]


def flight_pages():
    form = {
        "url": "https://www.google.com/travel/flights?hl=en",
        "title": "Flights",
        "text": "Trip type Round trip One way Multi-city From Ho Chi Minh City To destination Departure Return Search",
        "actions": [
            {"id": "f1", "kind": "select", "label": "Trip type Round trip", "node": 1, "value": "Round trip"},
            {"id": "f2", "kind": "fill", "label": "Where to destination", "node": 2, "value": ""},
            {"id": "f3", "kind": "click", "label": "Departure date", "node": 3},
            {"id": "f4", "kind": "click", "label": "Search flights", "node": 4},
        ],
    }
    typed = dict(form)
    typed["actions"] = [
        {"id": "f1", "kind": "select", "label": "Trip type Round trip", "node": 1, "value": "Round trip"},
        {"id": "f2", "kind": "fill", "label": "Where to destination", "node": 2, "value": "KUL"},
        {
            "id": "f2s",
            "kind": "click",
            "label": "Kuala Lumpur KUL International Airport",
            "node": 5,
        },
        {"id": "f3", "kind": "click", "label": "Departure date", "node": 3},
        {"id": "f4", "kind": "click", "label": "Search flights", "node": 4},
    ]
    typed["text"] = form["text"] + " Kuala Lumpur KUL International Airport suggestion"
    results = {
        "url": "https://www.google.com/travel/flights?hl=en&q=SGN-KUL",
        "title": "SGN to KUL flights",
        "text": (
            "One way Ho Chi Minh City SGN to Kuala Lumpur KUL 1 adult economy Departing flight options prices sorting"
        ),
        "actions": [
            {"id": "r1", "kind": "click", "label": "Sort by earliest departure", "node": 31},
            {"id": "r2", "kind": "click", "label": "Track prices", "node": 32},
        ],
    }
    return [form, typed, results]


def run_task(name, goal, page_flow, field_values):
    """Drive choose() through page_flow; fill/click advance pages, DONE ends."""
    history = []
    decisions = []
    page_idx = 0
    started = time.perf_counter()
    filled_fields = set()
    while True:
        page = page_flow[min(page_idx, len(page_flow) - 1)]
        page = dict(page)
        page["actions"] = [
            dict(a, value=field_values.get(a["id"], a.get("value", ""))) if a["id"] in filled_fields else dict(a)
            for a in page["actions"]
        ]
        d = mock.choose(page, goal, history)
        decisions.append(d)
        if d["choice"] in ("DONE", "BLOCKED"):
            ok = d["choice"] == "DONE"
            break
        action = next(a for a in page["actions"] if a["id"] == d["choice"])
        entry = {"choice": d["choice"], "kind": action["kind"]}
        if action["kind"] == "fill":
            ctx = mock.field_context(goal, action, page, history)
            value, helper = mock.field_text(ctx)
            entry["text"] = value
            filled_fields.add(action["id"])
            field_values = {**field_values, action["id"]: value}
        history.append(entry)
        if action["kind"] in ("click", "select") and page_idx < len(page_flow) - 1:
            page_idx += 1
        if len(decisions) > 20:
            ok = False
            break
    wall_ms = round((time.perf_counter() - started) * 1000)
    return {
        "task": name,
        "success": ok,
        "steps": len(history),
        "decisions": len(decisions),
        "backend_latency_ms": sum(d.get("latency_ms", 0) for d in decisions),
        "wall_ms": wall_ms,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--out", default="docs/benchmarks.md")
    args = ap.parse_args()

    tasks = [
        ("wikipedia", WIKI_GOAL, wiki_pages(), {}),
        ("flight-shape", FLIGHT_GOAL, flight_pages(), {}),
    ]
    runs = []
    t0 = time.perf_counter()
    for _ in range(args.runs):
        for name, goal, flow, fv in tasks:
            runs.append(run_task(name, goal, flow, dict(fv)))
    total_wall_ms = round((time.perf_counter() - t0) * 1000)

    # choose() latency distribution (offline, in-process): 200 timed calls.
    lat_samples = []
    for _ in range(200):
        s = time.perf_counter()
        mock.choose(wiki_pages()[0], WIKI_GOAL, [])
        lat_samples.append((time.perf_counter() - s) * 1000)
    lat_samples.sort()
    choose_latency_ms = {
        "n": len(lat_samples),
        "p50": round(lat_samples[len(lat_samples) // 2], 3),
        "p95": round(lat_samples[int(len(lat_samples) * 0.95)], 3),
        "max": round(lat_samples[-1], 3),
    }

    by_task = {}
    for r in runs:
        by_task.setdefault(r["task"], []).append(r)

    def stats(rs):
        n = len(rs)
        succ = sum(1 for r in rs if r["success"])
        steps = [r["steps"] for r in rs]
        decs = [r["decisions"] for r in rs]
        walls = [r["wall_ms"] for r in rs]
        lat = [r["backend_latency_ms"] for r in rs]
        return {
            "runs": n,
            "success": succ,
            "success_rate": round(succ / n, 3) if n else 0,
            "steps_median": sorted(steps)[n // 2],
            "steps_range": [min(steps), max(steps)],
            "decisions_median": sorted(decs)[n // 2],
            "backend_latency_ms_median": sorted(lat)[n // 2],
            "wall_ms_median": sorted(walls)[n // 2],
            "wall_ms_range": [min(walls), max(walls)],
        }

    summary = {name: stats(rs) for name, rs in by_task.items()}
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "backend": "backends.mock.model (offline, rule-based; no browser, no network)",
        "mode": "offline decision-layer replay (choose() over fixed page-shapes)",
        "total_wall_ms": total_wall_ms,
        "choose_latency_ms": choose_latency_ms,
        "summary": summary,
        "runs": runs,
    }
    root = Path(__file__).resolve().parent.parent
    (root / "docs" / "benchmarks.json").write_text(json.dumps(payload, indent=2) + "\n")

    lines = [
        "# Benchmarks",
        "",
        "Offline decision-layer replay: the rule-based mock backend's",
        "`choose()` over fixed page-shapes — no browser, no network, no",
        "paid APIs. Measures repeatability of the decision layer, not",
        "end-to-end browser runs.",
        "",
        "The live end-to-end proof is separate: `demos/wikipedia/run.py`",
        "runs a real browser against real Wikipedia (mock backend, offline",
        "decisions) and verifies exact article URL + title + body markers",
        "(latest verified run: 7 steps, 10 decisions, DONE).",
        "The flight demo needs live Google + Laya + text model and is not",
        "part of CI.",
        "",
        f"Generated {payload['generated_at']} · {args.runs} runs x 2 tasks · "
        f"total wall {total_wall_ms} ms. Raw evidence: `benchmarks.json`.",
        "",
        "| task | runs | success rate | steps (median) | backend calls (median) "
        "| backend latency ms (median) | wall ms (median) |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for name, s in summary.items():
        lines.append(
            f"| {name} | {s['runs']} | {s['success']}/{s['runs']} "
            f"({s['success_rate']:.0%}) | {s['steps_median']} "
            f"(range {s['steps_range'][0]}-{s['steps_range'][1]}) | "
            f"{s['decisions_median']} | {s['backend_latency_ms_median']} | "
            f"{s['wall_ms_median']} |"
        )
    lines += [
        "",
        "Columns: steps = actions executed (fill/click/select); backend calls",
        "= `choose()` decisions incl. terminal DONE/BLOCKED; backend latency",
        "= sum of `choose()` latency_ms per run; wall = measured wall time.",
        "",
        f"Mock `choose()` latency in-process (n={choose_latency_ms['n']}): "
        f"p50 {choose_latency_ms['p50']} ms, p95 {choose_latency_ms['p95']} ms, "
        f"max {choose_latency_ms['max']} ms. (Decision layer only — browser",
        "observation + page loads dominate live runs; the live wikipedia demo",
        "above reports 7 steps / 10 decisions end to end.)",
        "",
        "Reproduce: `uv run python scripts/bench_mock.py --runs 5` then",
        "`uv run pytest` (offline gates).",
        "",
    ]
    (root / args.out).write_text("\n".join(lines))
    print("\n".join(lines[11:14]))
    print("wrote", args.out, "and docs/benchmarks.json")


if __name__ == "__main__":
    main()
