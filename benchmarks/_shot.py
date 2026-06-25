"""Render a placements.json from several angles via the data-driven viewer (web/incr.html).

Usage: PYTHONPATH=. python benchmarks/_shot.py <placements.json> <out_prefix> [new_ref] [angles]
  e.g. PYTHONPATH=. python benchmarks/_shot.py out/rung2_placements.json out/r2a p_clamp iso,x,y,z
"""
import sys, json, http.server, socketserver, threading, functools
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PORT = 8762


def serve():
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), h)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def shoot(src="out/rung2_placements.json", prefix="out/shot", new="", angles=("iso", "x", "y", "z"), extra=""):
    """Render `src` placements from each angle to `{prefix}_{ang}.png`. Importable so the
    gate (and any verify step) can produce the actual rendered assembly automatically --
    looking at the render IS the verification, so it should never be a manual afterthought."""
    if isinstance(angles, str):
        angles = angles.split(",")
    src_url = "/" + str(Path(src)).replace("\\", "/")
    out_files = []
    httpd = serve()
    try:
        with sync_playwright() as pw:
            # software GL: hardware GL races on pixel readback here and yields blank frames
            b = pw.chromium.launch(args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader"])
            pg = b.new_page(viewport={"width": 1000, "height": 800})
            for ang in angles:
                url = f"http://127.0.0.1:{PORT}/web/incr.html?src={src_url}&dir={ang}&new={new}{extra}"
                pg.goto(url)
                pg.wait_for_function("window.__ready===true", timeout=20000)
                pg.wait_for_timeout(800)
                out = f"{prefix}_{ang}.png"
                pg.screenshot(path=out)
                out_files.append(out)
                print("wrote", out)
            b.close()
    finally:
        httpd.shutdown()
    return out_files


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "out/rung2_placements.json"
    prefix = sys.argv[2] if len(sys.argv) > 2 else "out/shot"
    new = sys.argv[3] if len(sys.argv) > 3 else ""
    angles = (sys.argv[4] if len(sys.argv) > 4 else "iso,x,y,z").split(",")
    shoot(src, prefix, new, angles)


if __name__ == "__main__":
    main()
