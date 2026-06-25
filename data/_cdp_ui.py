"""Minimal raw-CDP UI driver for eval-hostile Misumi pages (the detail/SPA pages wedge
Runtime.evaluate, so we drive them by screenshot + TRUSTED Input mouse events only).
Reconnects per call (stateless across Bash invocations)."""
from __future__ import annotations
import json, base64, time, urllib.request
from websocket import create_connection

PORT = 9222


def _hj(p):
    return json.loads(urllib.request.urlopen(f"http://127.0.0.1:{PORT}{p}", timeout=10).read())


class Conn:
    def __init__(self, ws_url, timeout=180):
        self.ws = create_connection(ws_url, timeout=timeout, suppress_origin=True)
        self._i = 0

    def send(self, method, **params):
        self._i += 1
        i = self._i
        self.ws.send(json.dumps({"id": i, "method": method, "params": params}))
        while True:
            m = json.loads(self.ws.recv())
            if m.get("id") == i:
                return m

    def close(self):
        try: self.ws.close()
        except Exception: pass


def browser():
    return Conn(_hj("/json/version")["webSocketDebuggerUrl"], timeout=30)


def page_for(url_substr):
    t = next(t for t in _hj("/json") if t["type"] == "page" and url_substr in t.get("url", ""))
    return Conn(t["webSocketDebuggerUrl"], timeout=180), t["id"]


def set_downloads(path_abs):
    b = browser()
    try:
        b.send("Browser.setDownloadBehavior", behavior="allow",
               downloadPath=path_abs, eventsEnabled=True)
    finally:
        b.close()


def shot(conn, out_png, clip=None):
    p = {"format": "png"}
    if clip:
        p["clip"] = {**clip, "scale": clip.get("scale", 1)}
    r = conn.send("Page.captureScreenshot", **p)
    open(out_png, "wb").write(base64.b64decode(r["result"]["data"]))
    return out_png


def click(conn, x, y):
    for typ in ("mousePressed", "mouseReleased"):
        conn.send("Input.dispatchMouseEvent", type=typ, x=x, y=y,
                  button="left", clickCount=1)
        time.sleep(0.05)
