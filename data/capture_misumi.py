"""All-tabs network capture for Misumi CAD downloads (learn the flow -> replay it).

Misumi's "Generate CAD" opens a NEW tab and fires the generate/download API there,
so listeners bound to pages[0] miss it (CLAUDE.md). This attaches request/response/
download listeners to EVERY existing page AND every page opened later (ctx.on("page")
+ page.on("popup")), and logs everything to out/misumi_capture.log with timestamps.

Run it (background), then in the user's Chrome click: CAD Download -> 3D -> STEP ->
Generate. The log then shows the exact generate API (URL + POST body) and the file
URL, which data/browse.py can replay hands-off.

    PYTHONPATH=. python data/capture_misumi.py            # 900s default
    PYTHONPATH=. python data/capture_misumi.py 600        # custom seconds
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAD = ROOT / "cad"
LOG = ROOT / "out" / "misumi_capture.log"

# URLs hitting these are logged in FULL (POST body + JSON response body).
INTEREST = ("cad", "CAD", "generate", "Generate", "download", "Download", "step",
            "STEP", "stp", "zip", "partcommunity", "3dfindit", "/api/", "ec/api",
            "HissuCode", "VonaDownload", "vona2/download", "fileDownload", "dxf",
            "parasolid", "iges", "ap203", "AP203", "cadenas")
# resource types we log at least a one-line summary for (skip the noise).
LOG_TYPES = {"xhr", "fetch", "document", "script", "other", "websocket"}


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


class Capture:
    def __init__(self, fh):
        self.fh = fh
        self.seen_pages = set()

    def log(self, *parts):
        line = " ".join(str(p) for p in parts)
        self.fh.write(line + "\n")
        self.fh.flush()
        print(line[:200])
        sys.stdout.flush()

    def _interesting(self, url: str) -> bool:
        return any(k in url for k in INTEREST)

    def attach(self, page, origin="existing"):
        pid = id(page)
        if pid in self.seen_pages:
            return
        self.seen_pages.add(pid)
        try:
            url = page.url
        except Exception:
            url = "?"
        self.log(f"[{_ts()}] +PAGE ({origin}) {url[:120]}")

        def on_request(req):
            try:
                rt = req.resource_type
                hot = self._interesting(req.url)
                if not hot and rt not in LOG_TYPES:
                    return                                  # skip image/css/font/media
                self.log(f"[{_ts()}] REQ [{rt}] {req.method} {req.url}")
                if hot:
                    post = req.post_data or ""
                    if post:
                        self.log(f"           POST-BODY: {post[:3000]}")
                    ref = (req.headers or {}).get("referer")
                    if ref:
                        self.log(f"           referer: {ref[:160]}")
            except Exception as e:
                self.log(f"[{_ts()}] req-err {e}")

        def on_response(resp):
            try:
                if not self._interesting(resp.url):
                    return
                ct = (resp.headers or {}).get("content-type", "")
                self.log(f"[{_ts()}] RESP {resp.status} {ct[:40]} {resp.url}")
                if "json" in ct or ("text" in ct and "html" not in ct):
                    try:
                        self.log(f"           BODY: {resp.text()[:3000]}")
                    except Exception:
                        pass
            except Exception as e:
                self.log(f"[{_ts()}] resp-err {e}")

        def on_download(dl):
            try:
                self.log(f"[{_ts()}] DOWNLOAD url={dl.url}")
                self.log(f"           suggested={dl.suggested_filename}")
                dest = CAD / dl.suggested_filename
                dl.save_as(str(dest))
                self.log(f"           SAVED -> {dest}")
            except Exception as e:
                self.log(f"[{_ts()}] download-err {e}")

        def on_popup(pop):
            self.log(f"[{_ts()}] POPUP from {url[:80]}")
            self.attach(pop, origin="popup")

        page.on("request", on_request)
        page.on("response", on_response)
        page.on("download", on_download)
        page.on("popup", on_popup)
        page.on("framenavigated", lambda fr: (fr == page.main_frame) and
                self.log(f"[{_ts()}] NAV {fr.url[:140]}"))


def main():
    from playwright.sync_api import sync_playwright

    dur = int(sys.argv[1]) if len(sys.argv) > 1 else 900
    CAD.mkdir(exist_ok=True)
    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, "w", encoding="utf-8") as fh, sync_playwright() as p:
        cap = Capture(fh)
        b = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        cap.log(f"[{_ts()}] connected; {len(b.contexts)} context(s)")
        def attach_ctx(ctx):
            for pg in ctx.pages:
                cap.attach(pg)
            ctx.on("page", lambda pg: cap.attach(pg, origin="new-tab"))

        for ctx in b.contexts:
            attach_ctx(ctx)

        # pick a live page to PUMP the sync-API event loop on (a bare time.sleep
        # loop never dispatches page.on callbacks -- you must call into Playwright).
        def a_page():
            for ctx in b.contexts:
                for pg in ctx.pages:
                    if not pg.url.startswith("chrome://"):
                        return pg
            return b.contexts[0].pages[0] if b.contexts and b.contexts[0].pages else None

        # self-test: reload a real page and confirm our listeners fire.
        pg0 = a_page()
        if pg0 and not pg0.url.startswith("chrome://"):
            cap.log(f"[{_ts()}] SELF-TEST reload {pg0.url[:70]}")
            try:
                pg0.reload(wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                cap.log(f"[{_ts()}] self-test reload err {str(e)[:80]}")

        cap.log(f"[{_ts()}] LISTENING for {dur}s -- click CAD Download -> 3D -> "
                f"STEP -> Generate in the DEBUG window (port 9222).")
        t0 = time.time()
        n_ctx = len(b.contexts)
        while time.time() - t0 < dur:
            pump = a_page()
            try:
                if pump:
                    pump.wait_for_timeout(500)   # <-- pumps event dispatch
                else:
                    time.sleep(0.5)
            except Exception:
                time.sleep(0.5)
            try:
                for ctx in b.contexts:
                    for pg in ctx.pages:
                        if id(pg) not in cap.seen_pages:
                            cap.attach(pg, origin="rescan")
                if len(b.contexts) != n_ctx:
                    n_ctx = len(b.contexts)
                    for ctx in b.contexts:
                        attach_ctx(ctx)
            except Exception:
                pass
        cap.log(f"[{_ts()}] done.")


if __name__ == "__main__":
    main()
