"""observe() -- render an assembly with its TRUE colours, then mark gate failures.

The render is the de-facto observation surface for VALIDITY, not just geometry. One
assembly definition (library + placements + attachment instances + ground) is run
through the load-path gate; the render keeps every part's OWN colour (so the picture
reads naturally), and any UNHELD body (e.g. a bolt pattern with 0 fasteners -> NOT
FASTENED, Hard Rule 6) is ringed with a RED BOX + label, plus a per-body verdict list.
So a broken/unfastened joint is observable in the picture, like a floating/scale error.

The red box is found WITHOUT the camera matrix: a second 'mask' render shows only the
unheld part, and its non-background pixels give the screen bbox.
"""
from __future__ import annotations
import json, socketserver
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ontology import load_path as LP
from benchmarks._shot import shoot

socketserver.TCPServer.allow_reuse_address = True   # allow back-to-back renders on the same port
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
BG = np.array([21, 23, 26])                          # incr.html scene background
_NAME = {LP.CONFIRMED: "HELD", LP.PROVISIONAL: "PROVISIONAL", LP.UNHELD: "UNHELD / NOT-FASTENED"}


def _rel(p): return str(Path(p).relative_to(ROOT)).replace("\\", "/")


def _mask_bbox(placements, ref, render_entry):
    """Render ONLY `ref` and return the screen bbox of its pixels (or None)."""
    one = {ref: placements[ref], "_render": [render_entry]}
    src = OUT / f"_mask_{ref}.json"; src.write_text(json.dumps(one))
    img = shoot(_rel(src), f"out/_mask_{ref}", "", ("iso",))[0]
    a = np.asarray(Image.open(img).convert("RGB"), dtype=int)
    fg = np.abs(a - BG).max(axis=2) > 28
    ys, xs = np.where(fg)
    return (xs.min(), ys.min(), xs.max(), ys.max()) if len(xs) else None


def observe(name, library, placements, instances, ground, render, *, mode="validation", angles=("iso",)):
    rep = LP.evaluate(instances, library, placements, ground, mode)
    # TRUE colours -- no recolouring of held parts
    src = OUT / f"{name}_observe_placements.json"
    out = dict(placements); out["_render"] = render
    src.write_text(json.dumps(out, indent=2))
    base = shoot(_rel(src), f"out/{name}_observe", "", angles)[0]

    img = Image.open(base).convert("RGB"); d = ImageDraw.Draw(img)
    try: F = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 15)
    except Exception: F = ImageFont.load_default()

    # red box around each UNHELD graded body (own colour kept; just ringed)
    by_ref = {e["ref"]: e for e in render}
    for ref, b in rep.bodies.items():
        if ref in ground or b.state != LP.UNHELD or ref not in by_ref:
            continue
        bb = _mask_bbox(placements, ref, by_ref[ref])
        if bb:
            d.rectangle([bb[0]-4, bb[1]-4, bb[2]+4, bb[3]+4], outline=(235, 60, 60), width=3)
            d.text((bb[0]-4, bb[3]+6), f"{ref}: NOT FASTENED", fill=(235, 90, 90), font=F)

    # verdict list (own colours stay; this is the legend)
    lines = [f"GATE ({mode})  ->  {'ALL HELD' if rep.all_confirmed else 'NOT ALL HELD'}"]
    for ref, b in sorted(rep.bodies.items()):
        if ref not in ground:
            lines.append(f"  {ref}: {_NAME[b.state]}")
    y = 10
    for i, t in enumerate(lines):
        c = ((255,255,255) if i == 0 else (120,230,120) if t.endswith("HELD") and "UN" not in t
             else (230,180,60) if "PROV" in t else (235,90,90))
        w = d.textlength(t, font=F); d.rectangle([8, y-2, 12+w, y+18], fill=(0,0,0)); d.text((10, y), t, fill=c, font=F)
        y += 21
    img.save(base)
    print(f"observed -> {base}  ({'ALL HELD' if rep.all_confirmed else 'NOT ALL HELD'})")
    return rep, base
