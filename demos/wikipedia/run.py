"""Search Wikipedia for "Ada Lovelace" and open the article.

Proves the backend contract: this demo runs on the rule-based mock
backend (offline, default) or the real Laya backend (`--laya`, needs
TEXT_MODEL_API_KEY for field text). Field values come only from the
quoted goal span — no site-specific values anywhere but GOAL.

Note: the Laya operation head currently bails to DONE on this
content-heavy page (README Limits), so the `--laya` path stops
immediately; the mock path runs the full search → article flow.
"""

import argparse
import sys

from ultrafast import Agent

GOAL = 'On Wikipedia, search for "Ada Lovelace" and open the Ada Lovelace mathematician article.'

ARTICLE_MARKERS = ("Charles Babbage", "Lord Byron")


def verify(agent):
    state = agent.state
    page = state["page"]
    text, title, url = page["text"], page["title"], page["url"]
    assert state["status"] == "done", f"agent stopped: {state['status']}"
    assert url.split("?")[0] == "https://en.wikipedia.org/wiki/Ada_Lovelace", f"not on the article page: {url}"
    assert all(m in text for m in ARTICLE_MARKERS), "article body missing markers"
    assert title == "Ada Lovelace - Wikipedia", f"unexpected title: {title}"
    attempts = [h for h in state["history"] if h["kind"] == "click"]
    assert attempts, "no suggestion click executed"
    done_steps = [d for d in state["decisions"] if d["choice"] == "DONE"]
    assert done_steps, "no DONE decision recorded"
    assert state["history"], "no actions executed"
    return {
        "url": url,
        "title": title,
        "steps": len(state["history"]),
        "decisions": len(state["decisions"]),
        "latency_ms": sum(d.get("latency_ms", 0) for d in state["decisions"]),
    }


def main(backend="backends.mock.model"):
    with Agent("https://en.wikipedia.org/wiki/Main_Page", GOAL, backend=backend) as agent:
        for snap in agent.run():
            d = snap["decisions"][-1] if snap["decisions"] else {}
            print(
                "%s [%s] conf=%.2f %dms"
                % (d.get("operation"), d.get("target"), d.get("confidence", 0), d.get("latency_ms", 0))
            )
        result = verify(agent)
        print("status:", agent.state["status"])
        print("verified:", result)
        return agent


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--laya", action="store_true", help="use the real Laya backend (:8770)")
    args = parser.parse_args()
    try:
        main("backends.laya.model" if args.laya else "backends.mock.model")
    except AssertionError as e:
        print("VERIFY FAILED:", e)
        sys.exit(1)
