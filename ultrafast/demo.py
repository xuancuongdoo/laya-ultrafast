"""Loopback-only inspector for the Laya browser agent: uv run laya-ultrafast."""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from ultrafast.agent import Agent

ROOT = Path(__file__).parent
PORT = int(os.environ.get("LAYA_DEMO_PORT", "8766"))
ORIGIN = f"http://127.0.0.1:{PORT}"

AGENT = None


def load_environment():
    path = Path.cwd() / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ.setdefault(key, value)


def snapshot():
    if AGENT is None:
        return {"status": "idle", "history": [], "decision": None, "page": None}
    return AGENT.snapshot()


class Handler(BaseHTTPRequestHandler):
    def send(self, status, content, mime="application/json"):
        content = content if isinstance(content, bytes) else content.encode()
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, *a, **k):
        pass

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/state":
            return self.send(200, json.dumps(snapshot(), default=str))
        if path == "/demo.mp4":
            video = ROOT.parent / "docs" / "demo.mp4"
            if video.exists():
                return self.send(200, video.read_bytes(), "video/mp4")
        if path in ("/", "/index.html"):
            return self.send(200, INDEX_HTML, "text/html; charset=utf-8")
        return self.send(404, "Not found", "text/plain")

    def do_POST(self):
        global AGENT
        path = urlparse(self.path).path
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0)) or 0) or b"{}")
        except Exception:
            return self.send(400, json.dumps({"error": "bad json"}))
        try:
            if path == "/api/start":
                goal = body.get("goal", "").strip()
                if not goal or len(goal) > 2000:
                    raise ValueError("Enter 1-2,000 characters")
                if AGENT:
                    AGENT.close()
                url = body.get("url") or "https://www.google.com/travel/flights?hl=en"
                AGENT = Agent(url, goal, screenshots=True)
            elif path == "/api/tick":
                if AGENT is None:
                    raise ValueError("Start a demo first")
                AGENT.command("tick", {})
            elif path == "/api/stop":
                if AGENT:
                    AGENT.close()
                    AGENT = None
            else:
                return self.send(404, json.dumps({"error": "unknown"}))
        except Exception as e:
            return self.send(400, json.dumps({"error": str(e)[:200]}))
        return self.send(200, json.dumps(snapshot(), default=str))


INDEX_HTML = Path(__file__).with_name("static_demo.html").read_text()


def main():
    load_environment()
    if not os.environ.get("TEXT_MODEL_API_KEY"):
        print("Note: TYPE_TEXT needs TEXT_MODEL_API_KEY in .env (decisions need no key).")
    print(f"Open {ORIGIN} and enter a goal.")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
