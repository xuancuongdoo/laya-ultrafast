"""SGN -> KUL end-to-end: the run from assets/demo.mp4.

One-way, 1 adult, economy, earliest date. Laya picks targets on :8770,
a small text model fills fields, guard approves the search click.
"""

from ultrafast import Agent


def _get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


GOAL = (
    "One-way flight Ho Chi Minh City (SGN) to Kuala Lumpur (KUL), "
    "1 adult economy. Set trip type One way, type destination KUL, "
    "pick the earliest departure date, click Search, stop when results load."
)

if __name__ == "__main__":
    with Agent("https://www.google.com/travel/flights?hl=en", GOAL, record_dir="./recordings") as agent:
        for snap in agent.run():
            decisions = _get(snap, "decisions") or []
            d = decisions[-1] if decisions else {}
            print(
                "%s [%s] conf=%.2f %dms"
                % (_get(d, "operation"), _get(d, "target"), _get(d, "confidence", 0), _get(d, "latency_ms", 0))
            )
        print("status:", _get(agent.state, "status"))
