import json, time, urllib.request
import websocket

PORT = 9222
TAB_ID = "93A244B82F846B30AA6EC8C8D8425B0B"


def get_ws_url(tab_id, port=PORT):
    d = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=8))
    for t in d:
        if t.get("id") == tab_id:
            return t["webSocketDebuggerUrl"]
    raise RuntimeError("tab not found")


class Page:
    def __init__(self, tab_id, port=PORT, timeout=60):
        self.ws = websocket.create_connection(get_ws_url(tab_id, port), max_size=64 * 1024 * 1024,
                                               suppress_origin=True, timeout=timeout)
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

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "nav"
    p = Page(TAB_ID, timeout=30)
    if cmd == "nav":
        url = sys.argv[2]
        p.navigate(url)
        time.sleep(3)
        print(p.evaluate("location.href"))
    elif cmd == "eval":
        expr = sys.argv[2]
        print(p.evaluate(expr))
    p.close()
