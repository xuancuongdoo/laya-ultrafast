"""Observed actions through Browser Harness; one CDP session, no per-step subprocess."""

import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

try:
    from browser_harness.admin import ensure_daemon
    from browser_harness.helpers import cdp
except ImportError:
    # fallback: direct CDP over websocket (CDP_PORT env, default 9333)
    import json as _json
    import urllib.request as _url

    def ensure_daemon():
        pass

    def cdp(method, session_id=None, **params):
        import websocket

        _base = "http://127.0.0.1:%s" % __import__("os").environ.get("CDP_PORT", "9333")
        if session_id is None:
            ts = _json.load(_url.urlopen(_base + "/json/list", timeout=10))
            tgt = [t for t in ts if t["type"] == "page"][-1]
            ws = websocket.create_connection(tgt["webSocketDebuggerUrl"], timeout=30)
        else:
            raise RuntimeError("session CDP needs browser_harness")
        _mid = [0]

        def send(m, p):
            _id = _mid[0]
            _mid[0] += 1
            ws.send(_json.dumps({"id": _id, "method": m, "params": p or {}}))
            while True:
                msg = _json.loads(ws.recv())
                if msg.get("id") == _id:
                    return msg.get("result", msg)

        return send(method, params)


from ultrafast.models import ActResult, ObservedAction, PageObservation

# Atomically read visible content and controls, preserving actual DOM node identity.
READ_STATE = Path(__file__).with_name("snapshot.js").read_text()
MARKER = f"(() => {{ const state={READ_STATE}; return state?.marker ?? null; }})()"


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _as_dict(obj: Any) -> dict:
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return dict(obj)


class StalePage(ValueError):
    """A decision no longer refers to the observed page."""


class Browser:
    def __init__(self, url):
        ensure_daemon()
        self.target = cdp("Target.createTarget", url="about:blank", background=True)["targetId"]
        self.session = cdp("Target.attachToTarget", targetId=self.target, flatten=True)["sessionId"]
        self.call("Emulation.setDeviceMetricsOverride", width=1120, height=780, deviceScaleFactor=1, mobile=False)
        # Keep rAF/menus rendering in an owned background tab, without activating the user's Chrome tab.
        self.call("Emulation.setFocusEmulationEnabled", enabled=True)
        self.call("Page.navigate", url=url)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if self.evaluate("document.readyState") == "complete":
                break
            time.sleep(0.02)

    def call(self, method, **params):
        return cdp(method, session_id=self.session, **params)

    def evaluate(self, expression):
        response = self.call("Runtime.evaluate", expression=expression, returnByValue=True)
        if response.get("exceptionDetails"):
            raise StalePage("Document changed during evaluation")
        return response.get("result", {}).get("value")

    def observe(self, screenshot=True) -> PageObservation:
        if getattr(self, "after_input", None):
            action, self.after_input = self.after_input, None
            action_dict = _as_dict(action)
            # This is read-only and happens after execution was logged, even if navigation interrupts it.
            try:
                self.call(
                    "Runtime.evaluate",
                    expression="""(action => new Promise(resolve => {
                      const field=window.__ultrafast?.nodes.get(action.node);
                      const autocomplete=action.kind==='fill' && field?.getAttribute('role')==='combobox';
                      let frames=0, stopped=false;
                      const finish=()=>{stopped=true;resolve()};
                      setTimeout(finish,autocomplete ? 200 : 50);
                      const ready=()=>{
                        if (stopped) return;
                        const ids=(field?.getAttribute('aria-controls')||field?.getAttribute('aria-owns')||'')
                          .split(/\\s+/).filter(Boolean);
                        const roots=ids.length ? ids.map(id=>document.getElementById(id)).filter(Boolean) : [document];
                        const options=roots.flatMap(root=>[...root.querySelectorAll('[role="option"]')]);
                        if (++frames>=2 && (!autocomplete || options.some(e=>{
                          const r=e.getBoundingClientRect();
                          return r.width && r.height && r.bottom>0 && r.top<innerHeight &&
                            e.checkVisibility({checkOpacity:true,checkVisibilityCSS:true});
                        }))) finish();
                        else requestAnimationFrame(ready);
                      };
                      requestAnimationFrame(ready);
                    }))("""
                    + json.dumps(action_dict)
                    + ")",
                    awaitPromise=True,
                    returnByValue=True,
                )
            except RuntimeError:
                pass
        for attempt in range(10):
            try:
                info = browser_operation({"operation": "observe", "session": self.session, "screenshot": screenshot})
                return PageObservation.from_dict(info)
            except StalePage:
                if attempt == 9:
                    raise
                time.sleep(0.02)
        raise StalePage("Page did not settle")

    def fresh(self, page, action=None) -> bool:
        page_d = _as_dict(page) if not isinstance(page, dict) else page
        if action is not None and _get(action, "kind") in {"click", "select"}:
            node = _get(action, "node")
            if type(node) is not int:
                return False
            current = self.evaluate(
                "(() => { const c=window.__ultrafast; "
                f"return c ? [c.pageKey(),c.guard(c.nodes.get({node}))] : null; }})()"
            )
            guards = _get(page, "guards") or {}
            return current == [_get(page, "page_key"), guards.get(str(node))]
        return self.evaluate(MARKER) == _get(page_d, "marker")

    def act(self, action, page, text=None) -> ActResult:
        if not self.fresh(page, action):
            raise StalePage("Page changed since this decision. Observe again.")
        action_d = _as_dict(action) if not isinstance(action, dict) else action
        if action_d["kind"] == "wait":
            time.sleep(0.1)
        result = browser_operation({"operation": "act", "session": self.session, "action": action_d, "text": text})
        self.after_input = action_d if action_d["kind"] != "wait" else None
        return ActResult.from_dict(result)

    def close(self):
        if self.target:
            cdp("Target.closeTarget", targetId=self.target)
            self.target = None


def fingerprint(state) -> str:
    if not isinstance(state, dict):
        state = state.to_dict()
    content = {k: state[k] for k in ("url", "text", "actions", "scroll")}
    return hashlib.sha256(json.dumps(content, sort_keys=True, default=str).encode()).hexdigest()


def browser_operation(request):
    operation = request["operation"]
    session = request["session"]

    def call(method, **params):
        return cdp(method, session_id=session, **params)

    def evaluate(expression):
        result = call("Runtime.evaluate", expression=expression, returnByValue=True)
        if result.get("exceptionDetails"):
            if operation == "act" and request["action"]["kind"] == "select":
                raise RuntimeError("Dropdown execution was interrupted; inspect before retrying.")
            raise StalePage("Document changed during evaluation")
        return result.get("result", {}).get("value")

    if operation == "act":
        action = request["action"]
        kind = action["kind"]
        if kind == "scroll":
            call("Input.dispatchMouseEvent", type="mouseWheel", x=550, y=650, deltaX=0, deltaY=action["delta"])
        elif kind != "wait":
            if type(action["node"]) is not int:
                raise ValueError("Invalid observed node")
            # Code-owned node IDs refer to actual observed elements, never model-generated selectors.
            target = evaluate(
                """(action => {
              const e=window.__ultrafast?.nodes.get(action.node);
              if (!e?.isConnected || e.matches(':disabled') || e.closest('[aria-disabled="true"],[inert]') ||
                  !e.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})) return null;
              if (action.kind==='fill' && (e.readOnly || e.getAttribute('aria-readonly')==='true')) return null;
              const r=e.getBoundingClientRect(), x=r.x+r.width/2, y=r.y+r.height/2;
              if (!r.width || !r.height || x<0 || y<0 || x>=innerWidth || y>=innerHeight) return null;
              if (!e.contains(document.elementFromPoint(x,y))) return null;
              if (action.kind==='select') {
                if (e.tagName!=='SELECT' || ![...e.options].some(o=>o.value===action.value &&
                    !o.disabled && !o.closest('optgroup[disabled]'))) return null;
                e.value=action.value;
                e.dispatchEvent(new Event('input',{bubbles:true}));
                e.dispatchEvent(new Event('change',{bubbles:true}));
              }
              return {x,y};
            })("""
                + json.dumps(action)
                + ")"
            )
            if target is None:
                if kind == "select":
                    raise RuntimeError("Dropdown execution was not confirmed; inspect before retrying.")
                raise StalePage("Target changed or is covered. Observe again.")
            if kind != "select":
                x, y = target["x"], target["y"]
                for event in ("mousePressed", "mouseReleased"):
                    call("Input.dispatchMouseEvent", type=event, x=x, y=y, button="left", clickCount=1)
                if kind == "fill":
                    call(
                        "Input.dispatchKeyEvent",
                        type="keyDown",
                        key="a",
                        code="KeyA",
                        modifiers=4 if sys.platform == "darwin" else 2,
                        commands=["selectAll"],
                    )
                    call(
                        "Input.dispatchKeyEvent",
                        type="keyUp",
                        key="a",
                        code="KeyA",
                        modifiers=4 if sys.platform == "darwin" else 2,
                    )
                    call("Input.insertText", text=request["text"])
        return {"executed": action["id"]}

    info = evaluate(READ_STATE)
    if info is None:
        raise StalePage("Document is navigating")
    info["fingerprint"] = fingerprint(info)
    if request.get("screenshot", True):
        info["screenshot"] = call("Page.captureScreenshot", format="jpeg", quality=72)["data"]
    return info


__all__ = ["Browser", "ObservedAction", "PageObservation", "StalePage", "browser_operation", "fingerprint"]
