"""Tiny helper: connect raw CDP to a SPECIFIC tab id (not URL substring), so a
concurrent scout never risks grabbing another scout's tab. Throwaway scout-local
utility -- not part of the canonical pipeline."""
from __future__ import annotations
import json
import urllib.request
import websocket


class TabPage:
    def __init__(self, tab_id: str, port: int = 9222, timeout: int = 120):
        d = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=8))
        url = None
        for t in d:
            if t.get("id") == tab_id:
                url = t["webSocketDebuggerUrl"]
                break
        if not url:
            raise RuntimeError(f"tab {tab_id} not found")
        self.ws = websocket.create_connection(url, max_size=64 * 1024 * 1024, suppress_origin=True)
        self.ws.settimeout(timeout)
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
        import base64
        open(path, "wb").write(base64.b64decode(r["data"]))
        return path

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass
