"""Scout helper for the plain M5 T-slot nut (8 mm slot) search.

Own-tab raw CDP driver for one part-evidence-scout. Creates its OWN target,
operates on it, and closes it on cleanup (per CDP hygiene rules).
"""
from __future__ import annotations

import base64
import json
import time
import urllib.request
import websocket

CDP_PORT = 9222
BASE_URL = "https://us.misumi-ec.com/vona2/pc/system/api"


def _browser_ws():
    d = json.load(urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json/version", timeout=8))
    return d["webSocketDebuggerUrl"]


def _list_targets():
    return json.load(urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json/list", timeout=8))


def create_target(url: str) -> str:
    """Open a NEW tab on the warm browser via the browser CDP socket."""
    bws = websocket.create_connection(_browser_ws(), max_size=64 * 1024 * 1024,
                                      suppress_origin=True)
    bws.settimeout(60)
    try:
        mid = 1
        bws.send(json.dumps({"id": mid, "method": "Target.createTarget",
                             "params": {"url": url}}))
        while True:
            msg = json.loads(bws.recv())
            if msg.get("id") == mid:
                tid = msg["result"]["targetId"]
                # fetch this target's ws url
                for t in _list_targets():
                    if t.get("id") == tid:
                        return t["webSocketDebuggerUrl"]
                raise RuntimeError(f"target {tid} not in list")
    finally:
        bws.close()


def close_target(target_id: str):
    bws = websocket.create_connection(_browser_ws(), max_size=64 * 1024 * 1024,
                                      suppress_origin=True)
    bws.settimeout(30)
    try:
        mid = 1
        bws.send(json.dumps({"id": mid, "method": "Target.closeTarget",
                             "params": {"targetId": target_id}}))
        while True:
            msg = json.loads(bws.recv())
            if msg.get("id") == mid:
                return msg.get("result", {})
    finally:
        bws.close()


class Tab:
    """Raw CDP over ONE page target (its own tab)."""

    def __init__(self, ws_url: str, target_id: str):
        self.target_id = target_id
        self.ws = websocket.create_connection(ws_url, max_size=64 * 1024 * 1024,
                                              suppress_origin=True)
        self.ws.settimeout(120)
        self._id = 0
        self._send("Runtime.enable")
        self._send("Page.enable")

    def _send(self, method, **params):
        self._id += 1
        mid = self._id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    def evaluate(self, expr, await_promise=False):
        r = self._send("Runtime.evaluate", expression=expr, returnByValue=True,
                       awaitPromise=await_promise, allowUnsafeEvalBlocklist=False)
        res = r.get("result", {})
        if "value" in res:
            return res["value"]
        return res.get("description")

    def navigate(self, url):
        return self._send("Page.navigate", url=url)

    def screenshot(self, path, clip=None):
        params = {"format": "png"}
        if clip:
            params["clip"] = {**clip, "scale": clip.get("scale", 1)}
        r = self._send("Page.captureScreenshot", **params)
        open(path, "wb").write(base64.b64decode(r["data"]))
        return path

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


def open_tab(url: str) -> Tab:
    ws_url = create_target(url)
    # target_id is the last path segment of ws url? No: parse from list.
    tid = None
    for t in _list_targets():
        if t.get("webSocketDebuggerUrl") == ws_url:
            tid = t.get("id")
            break
    return Tab(ws_url, tid)
