"""Incremental, VISUAL attachment check. Walks the assembly in anchor-first order;
at each step renders the cumulative parts with the newly-added one highlighted, from
two angles, so each interface can be judged by EYE. Visual plausibility is the check
here -- no bounding boxes, no FCL distances (they produced false confidence and were
removed); if it doesn't look attached, it isn't.

Run:  PYTHONPATH=. python benchmarks/_shot_incremental.py
Out:  out/incr/NN_<ref>_<angle>.png
"""
import json, http.server, socketserver, threading, functools
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "incr"; OUT.mkdir(parents=True, exist_ok=True)
PORT = 8761

# real-parts Rung-2 (no CUSTOM boxes). Order is anchor-first: frame -> guide ->
# drive -> belt -> bridge.
URL = {"p_ext":"/cad/6575N368.glb","p_rail":"/cad/6709K231.glb",
       "p_carriage":"/cad/6709K211.glb","p_scr1":"/cad/90263A239.glb",
       "p_idl1":"/cad/3693N11.glb","p_scr2":"/cad/90263A239.glb",
       "p_idl2":"/cad/3693N11.glb","p_belt":"/cad/belt_gt2.glb",
       "p_bracket":"/cad/19155A34.glb","p_clamp":"/cad/TBCN2-6.glb"}
COLOR = 0x6a7178
ORDER = ["p_ext","p_rail","p_carriage","p_scr1","p_idl1","p_scr2","p_idl2",
         "p_belt","p_bracket","p_clamp"]
ANGLES = ["iso", "x"]


def serve():
    h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), h)
    threading.Thread(target=httpd.serve_forever, daemon=True).start(); return httpd


def main():
    place = json.load(open(ROOT / "out" / "rung2_placements.json"))
    httpd = serve()
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader"])
        pg = b.new_page(viewport={"width":900,"height":720})
        for i, ref in enumerate(ORDER):
            incl = ORDER[:i+1]
            sub = {r: place[r] for r in incl}
            sub["_render"] = [{"ref": r, "url": URL[r], "color": COLOR} for r in incl]
            fp = OUT / f"_step{i:02d}.json"; json.dump(sub, open(fp, "w"))
            for ang in ANGLES:
                url = f"http://127.0.0.1:{PORT}/web/incr.html?src=/out/incr/_step{i:02d}.json&dir={ang}&new={ref}"
                pg.goto(url); pg.wait_for_function("window.__ready===true", timeout=15000)
                pg.wait_for_timeout(800)
                pg.screenshot(path=str(OUT / f"{i:02d}_{ref}_{ang}.png"))
        b.close()
    httpd.shutdown()
    print("\nwrote", len(ORDER)*len(ANGLES), "images to out/incr/")


if __name__ == "__main__":
    main()
