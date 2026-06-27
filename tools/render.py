"""Render a placements.json from several angles via the data-driven viewer (viewer/incr.html).

Usage: PYTHONPATH=. python tools/render.py <placements.json> <out_prefix> [new_ref] [angles]
  e.g. PYTHONPATH=. python tools/render.py projects/rung3_rotary/out/rung3_assembly.json out/r2a p_clamp iso,x,y,z
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import server

def shoot(src="projects/rung3_rotary/out/rung3_assembly.json", prefix="out/shot", new="", angles=("iso", "x", "y", "z"), extra=""):
    """Render `src` placements from each angle to `{prefix}_{ang}.png`."""
    if isinstance(angles, str):
        angles = angles.split(",")
    try:
        rel_src = Path(src).relative_to(ROOT)
    except ValueError:
        rel_src = Path(src)
    src_url = "/" + str(rel_src).replace("\\", "/").replace("projects/", "")
    out_files = []
    
    PORT = 8765
    httpd = server.serve(port=PORT, block=False)
    
    try:
        with sync_playwright() as pw:
            # software GL: hardware GL races on pixel readback here and yields blank frames
            b = pw.chromium.launch(args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader"])
            pg = b.new_page(viewport={"width": 1000, "height": 800})
            pg.on("console", lambda msg: print(f"CONSOLE [{msg.type}]: {msg.text}"))
            pg.on("pageerror", lambda err: print(f"PAGEERROR: {err}"))
            pg.on("requestfailed", lambda req: print(f"REQUEST FAILED: {req.url}"))
            pg.on("response", lambda res: print(f"RESPONSE: {res.url} -> {res.status}") if res.status >= 400 else None)
            first = True
            for ang in angles:
                if first:
                    url = f"http://127.0.0.1:{PORT}/_app/incr.html?src={src_url}&dir={ang}&new={new}{extra}"
                    pg.goto(url)
                    pg.wait_for_function("window.__ready===true", timeout=20000)
                    pg.wait_for_timeout(800)
                    first = False
                else:
                    pg.evaluate(f"window.frameCamera('{ang}')")
                    pg.wait_for_timeout(100)
                out = f"{prefix}_{ang}.png"
                pg.screenshot(path=out)
                out_files.append(out)
                print("wrote", out)
            b.close()
    finally:
        if httpd:
            httpd.shutdown()
            httpd.server_close()
    return out_files

def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "projects/rung3_rotary/out/rung3_assembly.json"
    prefix = sys.argv[2] if len(sys.argv) > 2 else "out/shot"
    new = sys.argv[3] if len(sys.argv) > 3 else ""
    angles = (sys.argv[4] if len(sys.argv) > 4 else "iso,x,y,z").split(",")
    shoot(src, prefix, new, angles)

if __name__ == "__main__":
    main()
