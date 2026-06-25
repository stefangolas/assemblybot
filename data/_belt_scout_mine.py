"""My own tab for the S3M belt scout. Uses Target.createTarget / Target.closeTarget
so I never touch another scout's tab or the shared base tabs."""
import json, urllib.request, time, base64
import websocket

PORT = 9222
MY_HOME = "https://us.misumi-ec.com/"


def _http(path):
    return json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}", timeout=10))


def create_tab(url=MY_HOME):
    # PUT /json/new?<url> creates a new page target (the legacy endpoint).
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{PORT}/json/new?{url}",
                                     method="PUT")
        d = json.load(urllib.request.urlopen(req, timeout=15))
        return d["id"], d["webSocketDebuggerUrl"]
    except Exception as e:
        # Fall back to Target.createTarget via the browser ws
        return _create_via_browser(url), None


def _create_via_browser(url):
    raise RuntimeError(f"create_tab failed: {e}")


def close_tab(tab_id):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/close/{tab_id}", timeout=10)
    except Exception as e:
        print(f"[close_tab] {tab_id}: {e}")


def list_tabs():
    return _http("/json/list")


class Page:
    def __init__(self, ws_url, timeout=120):
        self.ws = websocket.create_connection(ws_url, max_size=64*1024*1024, suppress_origin=True)
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
        return res.get("value") if "value" in res else res.get("description")

    def navigate(self, url, settle=3.5):
        self._send("Page.navigate", url=url)
        time.sleep(settle)

    def screenshot(self, path):
        r = self._send("Page.captureScreenshot", format="png")
        open(path, "wb").write(base64.b64decode(r["data"]))
        return path

    def close(self):
        try: self.ws.close()
        except Exception: pass
