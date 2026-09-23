"""SGN -> KUL end-to-end: the run from assets/demo.mp4.

One-way, 1 adult, economy, earliest date. Laya picks targets on :8770,
a small text model fills fields, guard approves the search click.
"""
import sys

sys.path.insert(0, "..")
from laya_agent import LayaAgent

GOAL = (
    "One-way flight Ho Chi Minh City (SGN) to Kuala Lumpur (KUL), "
    "1 adult economy. Set trip type One way, type destination KUL, "
    "pick the earliest departure date, click Search, stop when results load."
)

if __name__ == "__main__":
    with LayaAgent("https://www.google.com/travel/flights?hl=en",
                   GOAL, record_dir="./recordings") as agent:
        for snap in agent.run():
            d = snap["decisions"][-1] if snap["decisions"] else {}
            print("%s [%s] conf=%.2f %dms" % (
                d.get("operation"), d.get("target"),
                d.get("confidence", 0), d.get("latency_ms", 0)))
        print("status:", agent.state["status"])
