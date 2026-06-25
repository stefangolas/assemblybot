"""Pin a Page() to a specific known target id (avoid substring collisions with other scouts)."""
import json
import urllib.request
import websocket


class PageById:
    def __init__(self, target_id, port=9222, timeout=120):
        d = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=8))
        ws_url = None
        for t in d:
            if t.get("id") == target_id:
                ws_url = t["webSocketDebuggerUrl"]
                break
        if not ws_url:
            raise RuntimeError(f"target {target_id} not found")
        self.ws = websocket.create_connection(ws_url, max_size=64 * 1024 * 1024, suppress_origin=True)
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

    def screenshot(self, path, fmt="png"):
        r = self._send("Page.captureScreenshot", format=fmt)
        import base64
        data = base64.b64decode(r["data"])
        with open(path, "wb") as f:
            f.write(data)
        return path
