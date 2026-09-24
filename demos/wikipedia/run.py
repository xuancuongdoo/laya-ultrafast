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
from ultrafast.models import VerificationResult

GOAL = 'On Wikipedia, search for "Ada Lovelace" and open the Ada Lovelace mathematician article.'

ARTICLE_MARKERS = ("Charles Babbage", "Lord Byron")


def _get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def verify(agent) -> VerificationResult:
    state = agent.state
    page = state.page if hasattr(state.page, "url") else state["page"]
    text, title, url = _get(page, "text"), _get(page, "title"), _get(page, "url")
    assert _get(state, "status") == "done", f"agent stopped: {_get(state, 'status')}"
    assert url.split("?")[0] == "https://en.wikipedia.org/wiki/Ada_Lovelace", f"not on the article page: {url}"
    assert all(m in text for m in ARTICLE_MARKERS), "article body missing markers"
    assert title == "Ada Lovelace - Wikipedia", f"unexpected title: {title}"
    history = _get(state, "history")
    attempts = [h for h in history if _get(h, "kind") == "click"]
    assert attempts, "no suggestion click executed"
    decisions = _get(state, "decisions")
    done_steps = [d for d in decisions if _get(d, "choice") == "DONE"]
    assert done_steps, "no DONE decision recorded"
    assert history, "no actions executed"
    return VerificationResult(
        url=url,
        title=title,
        steps=len(history),
        decisions=len(decisions),
        latency_ms=sum(_get(d, "latency_ms", 0) for d in decisions),
    )


def main(backend="backends.mock.model"):
    with Agent("https://en.wikipedia.org/wiki/Main_Page", GOAL, backend=backend) as agent:
        for snap in agent.run():
            decisions = _get(snap, "decisions") or []
            d = decisions[-1] if decisions else {}
            print(
                "%s [%s] conf=%.2f %dms"
                % (_get(d, "operation"), _get(d, "target"), _get(d, "confidence", 0), _get(d, "latency_ms", 0))
            )
        result = verify(agent)
        print("status:", _get(agent.state, "status"))
        print("verified:", result.to_dict())
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
