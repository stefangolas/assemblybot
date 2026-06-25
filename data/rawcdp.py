"""Raw Chrome DevTools Protocol over a single PAGE websocket.

Playwright's connect_over_cdp attaches to EVERY target (pages, iframes, workers)
and hangs when a flaky one is present -- on Misumi the Drift chat iframes +
service workers respawn on each SPA load and reliably wedge the connect. This
helper opens a raw websocket to ONE page target's webSocketDebuggerUrl and speaks
JSON-RPC directly, so it never touches those targets. Enough for: read the live
part number, set configurator inputs via JS, and run the in-page Misumi CAD fetch.
"""
from __future__ import annotations

import json
import urllib.request

import websocket  # websocket-client (sync)


def page_ws_url(url_substr: str, port: int = 9222) -> str:
    d = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=8))
    for t in d:
        if t.get("type") == "page" and url_substr in t.get("url", ""):
            return t["webSocketDebuggerUrl"]
    raise RuntimeError(f"no page target matching {url_substr!r}")


class Page:
    def __init__(self, url_substr="misumi", port=9222, timeout=120):
        # Chrome rejects WS handshakes carrying a browser Origin header unless
        # launched with --remote-allow-origins; suppress the Origin so it passes.
        self.ws = websocket.create_connection(page_ws_url(url_substr, port),
                                               max_size=64 * 1024 * 1024,
                                               suppress_origin=True)
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
            # ignore events

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
