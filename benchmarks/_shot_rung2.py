"""Headless screenshots of the Rung-2 viewer from several angles (verification).
Serves the repo root so /out and /cad resolve, drives the Three.js camera via the
__cam/__controls hooks the viewer exposes, and writes out/r2d_<angle>.png."""
import http.server, socketserver, threading, functools, time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PORT = 8753
# target near the belt/pulley centroid (metres): x=0.025, y=0.013, z=0
TGT = [0.012, 0.013, 0.0]
VIEWS = {                       # camera position (m) for each named angle
    "iso":   [0.16, 0.12, 0.18],
    "side":  [0.34, 0.013, 0.0],   # look along -Z (down the travel axis end)... actually +X
    "front": [0.012, 0.013, 0.34], # look along -Z
    "top":   [0.012, 0.34, 0.001], # look down -Y
}


def serve():
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), h)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def main():
    httpd = serve()
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 900, "height": 720})
        pg.goto(f"http://127.0.0.1:{PORT}/web/index.html")
        pg.wait_for_timeout(2500)        # let glTFs load
        for name, pos in VIEWS.items():
            pg.evaluate(
                """([p,t]) => { window.__cam.position.set(p[0],p[1],p[2]);
                   window.__controls.target.set(t[0],t[1],t[2]); window.__controls.update(); }""",
                [pos, TGT])
            pg.wait_for_timeout(400)
            pg.screenshot(path=str(ROOT / "out" / f"r2d_{name}.png"))
            print("wrote", f"out/r2d_{name}.png")
        b.close()
    httpd.shutdown()


if __name__ == "__main__":
    main()
