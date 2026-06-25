"""Cross-section render of the rung-3 core stack -- the formal 'section render' deliverable.

Cuts the ASSEMBLED stack (base -> RU85 -> adapter -> 72T pulley) at the axis plane and
renders the cut face, so the internal interfaces are visible: which bearing RACE each
part touches, the adapter inner-race boss + 0.5 mm relief, the pulley pilot, and the
Ø45 pass-through running clear through the whole stack (task Section 6 section renders).
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parent.parent
OUT, CAD = ROOT / "out", ROOT / "cad"

PARTS = [  # ref -> glb (core stack only, for a clean cross-section)
    ("p_base", "ROTARY_BASE_RU85_REV_A.glb",       [0.54, 0.56, 0.59]),
    ("p_brg",  "RU85UUC0.glb",                      [0.71, 0.65, 0.26]),
    ("p_adp",  "ROTARY_ADAPTER_RU85_S5M_REV_A.glb", [0.75, 0.34, 0.25]),
    ("p_72",   "HTPA72S5M150.glb",                  [0.29, 0.50, 0.69]),
]


def main():
    pl = json.loads((OUT / "rung3_redesign_placements.json").read_text())
    I = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    place, render = {}, []
    hexcol = {"p_base": 0x8a9097, "p_brg": 0xb5a642, "p_adp": 0xc0563f, "p_72": 0x4a7fb0}
    for ref, glb, _ in PARTS:
        m = trimesh.load(str(CAD / glb), force="mesh")
        R = np.array(pl[ref]["R"], float)
        t_m = np.array(pl[ref]["t_mm"], float) / 1000.0     # mm -> m (glb is metres)
        T = np.eye(4); T[:3, :3] = R; T[:3, 3] = t_m
        m.apply_transform(T)
        cut = m.slice_plane(plane_origin=[0, 0, 0], plane_normal=[0, 1, 0])  # keep Y<=0
        if cut is None or not len(cut.vertices):
            continue
        out = CAD / f"_sec_{ref}.glb"; cut.export(str(out))       # one glb per part -> own color
        place[ref] = {"R": I, "t_mm": [0, 0, 0]}
        render.append({"ref": ref, "url": f"/cad/_sec_{ref}.glb", "color": hexcol[ref]})
    print(f"wrote {len(render)} cut bodies (color-coded)")
    place["_render"] = render
    (OUT / "rung3_section_placements.json").write_text(json.dumps(place))
    try:
        from benchmarks._shot import shoot
        shoot("out/rung3_section_placements.json", "out/rung3_section", "", ("y", "iso"))
        print("rendered out/rung3_section_{y,iso}.png")
    except Exception as e:  # noqa: BLE001
        print(f"(render skipped: {e})")


if __name__ == "__main__":
    main()
