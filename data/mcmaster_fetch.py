"""McMaster CAD/spec fetch over raw CDP in the warm cdp-chrome (memory: mcmaster-cdp-download).

Generic hardware (shoulder screws, shims, washers, T-slot nuts) defaults to McMaster.
Three quirks, all handled here:
  (a) the product page is a JS shell over plain HTTP -> must use the rendered browser;
  (b) the CAD `<a download>.STEP` lazy-renders ONLY on the ACTIVE tab -> we createTarget
      + activateTarget a FRESH tab and poll it;
  (c) the download needs a TRUSTED gesture -> Input.dispatchMouseEvent at the link centre
      (a synthetic .click()/in-page fetch both fail/403).

Never relaunches Chrome. Reuses the running instance on :9222.
"""
from __future__ import annotations

import json
import shutil
import time
import urllib.request
from pathlib import Path

import websocket

ROOT = Path(__file__).resolve().parent.parent
CAD = ROOT / "cad"
DOWNLOADS = Path.home() / "Downloads"


def _http(path, port=9222):
    return json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json{path}", timeout=8))


class _WS:
    def __init__(self, ws_url, timeout=90):
        self.ws = websocket.create_connection(ws_url, max_size=64 * 1024 * 1024,
                                               suppress_origin=True)
        self.ws.settimeout(timeout)
        self._id = 0

    def send(self, method, **params):
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
        r = self.send("Runtime.evaluate", expression=expr, returnByValue=True,
                      awaitPromise=await_promise)
        res = r.get("result", {})
        return res.get("value", res.get("description"))

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


def open_active(pn, port=9222) -> tuple[_WS, str]:
    """Create a FRESH ACTIVE tab on the McMaster product page; return (ws, targetId)."""
    binfo = _http("/version", port)
    bws = _WS(binfo["webSocketDebuggerUrl"])
    tid = bws.send("Target.createTarget", url=f"https://www.mcmaster.com/{pn}/")["targetId"]
    bws.send("Target.activateTarget", targetId=tid)
    bws.close()
    # attach to the new tab
    ws_url = None
    for _ in range(20):
        for t in _http("/list", port):
            if t.get("id") == tid and t.get("type") == "page":
                ws_url = t["webSocketDebuggerUrl"]
        if ws_url:
            break
        time.sleep(0.5)
    pg = _WS(ws_url)
    pg.send("Page.enable"); pg.send("Runtime.enable")
    return pg, tid


def read_specs(pn, port=9222, wait=12) -> dict:
    """Open the page and return {title, text}. title bare 'McMaster-Carr' => invalid/shell."""
    pg, tid = open_active(pn, port)
    title, text = "", ""
    for _ in range(wait):
        title = pg.evaluate("document.title") or ""
        if title and title != "McMaster-Carr":
            text = pg.evaluate("document.body.innerText") or ""
            break
        time.sleep(1)
    pg.close()
    return {"pn": pn, "title": title, "text": text, "target": tid}


def download_step(pn, port=9222, poll=40, prefer_no_threads=False) -> Path | None:
    """Fetch <PN>.STEP via the active-tab + trusted-click flow; move to cad/<PN>.step."""
    binfo = _http("/version", port)
    bws = _WS(binfo["webSocketDebuggerUrl"])
    bws.send("Browser.setDownloadBehavior", behavior="allow",
             downloadPath=str(DOWNLOADS), eventsEnabled=True)
    bws.close()
    pg, tid = open_active(pn, port)
    title = ""
    link = None
    for _ in range(poll):
        title = pg.evaluate("document.title") or ""
        # find an <a download> ending .STEP and its bounding rect centre
        link = pg.evaluate(r"""
            (() => {
              const as=[...document.querySelectorAll('a[download]')];
              const a=as.find(x=>/\.STEP$/i.test(x.getAttribute('href')||''));
              if(!a) return null;
              const r=a.getBoundingClientRect();
              return {href:a.getAttribute('href'), x:r.x+r.width/2, y:r.y+r.height/2,
                      vis:r.width>0&&r.height>0};
            })()
        """)
        if link and link.get("vis"):
            break
        time.sleep(1)
    if not link or not link.get("vis"):
        pg.close()
        return None
    # trusted click at the link centre
    for kind in ("mousePressed", "mouseReleased"):
        pg.send("Input.dispatchMouseEvent", type=kind, x=link["x"], y=link["y"],
                button="left", clickCount=1)
    # wait for the file to land in Downloads
    dst = CAD / f"{pn}.step"
    for _ in range(30):
        cands = sorted(DOWNLOADS.glob(f"{pn}*.STEP"), key=lambda p: p.stat().st_mtime)
        crdl = list(DOWNLOADS.glob(f"{pn}*.crdownload"))
        if cands and not crdl:
            shutil.move(str(cands[-1]), str(dst))
            pg.close()
            return dst
        time.sleep(1)
    pg.close()
    return None


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "spec":
        r = read_specs(sys.argv[2])
        print("TITLE:", r["title"])
        print(r["text"][:2000])
    elif len(sys.argv) > 1 and sys.argv[1] == "cad":
        print(download_step(sys.argv[2]))
