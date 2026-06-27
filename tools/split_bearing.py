"""Split a roller-bearing glb into INNER-ring and OUTER-ring bodies.

A crossed-roller / ball bearing is one catalog part (one mesh), but kinematically
it is two bodies -- a stationary ring and a rotating ring sharing one axis -- plus
the rollers between them. The CADENAS/THK glb fuses them into a single geometry, but
that geometry is already made of many disconnected connected-components (the ring
walls, faces, each roller). They partition cleanly by radius from the bearing axis:
the inner ring sits at small r, the outer ring at large r, rollers in the band between.

So the split is just: connected-component the mesh, bin each component to inner/outer
by its mean radius vs a split radius, write two glbs (metres, like every other part).
Rollers (the middle band) go with the INNER ring by default -- they spin with it and,
being small, read fine either way; pass --rollers outer to flip.

This is for visual validation + correct kinematics (the DOF slider rotates the inner
ring while the outer stays put). It is NOT a watertight solid split; it is a faithful
render-and-articulate split, which is what the LOOK needs.

Usage:
  python -m tools.split_bearing RU85UUC0 --r-split 43.75
  python -m tools.split_bearing RU66UUC0           # r-split auto from bbox
"""
from __future__ import annotations
import argparse
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parent.parent
CAD = ROOT / "cad"


def split_bearing(pn: str, axis: str = "x", r_split_mm: float | None = None,
                  rollers: str = "inner") -> dict:
    """Split cad/<pn>.glb -> cad/<pn>_inner.glb + cad/<pn>_outer.glb (metres).

    axis: bearing rotation axis in the part-local frame ('x'|'y'|'z'). For the THK RU
          rings as authored, the axis is local X (rings span X=0..width).
    r_split_mm: components with mean radius below this -> inner, above -> outer. If
          None, use the midpoint between the global min and max radius (works because
          the rings are the radial extremes).
    rollers: 'inner' or 'outer' -- which ring the mid-band components attach to.
    """
    src = CAD / f"{pn}.glb"
    g = trimesh.load(src, force="mesh")
    comps = g.split(only_watertight=False)
    if len(comps) < 2:
        raise SystemExit(f"{pn}: only {len(comps)} component(s) -- cannot split by component")

    ai = {"x": 0, "y": 1, "z": 2}[axis]
    radial = [i for i in (0, 1, 2) if i != ai]

    def comp_radius_mm(c):
        v = c.vertices * 1000.0
        r = np.sqrt(v[:, radial[0]] ** 2 + v[:, radial[1]] ** 2)
        return float(r.mean()), float(r.min()), float(r.max())

    all_r = np.sqrt((g.vertices[:, radial[0]] * 1000) ** 2 + (g.vertices[:, radial[1]] * 1000) ** 2)
    r_lo, r_hi = float(all_r.min()), float(all_r.max())
    if r_split_mm is None:
        r_split_mm = 0.5 * (r_lo + r_hi)

    # roller band: assign to the chosen ring, but still bin by the split radius for
    # the ring walls themselves. A component is a "roller/cage" if its radial span
    # straddles the split radius; pure ring components sit entirely on one side.
    inner_parts, outer_parts = [], []
    for c in comps:
        rmean, rmin, rmax = comp_radius_mm(c)
        straddles = rmin < r_split_mm < rmax
        if straddles:
            (inner_parts if rollers == "inner" else outer_parts).append(c)
        elif rmean < r_split_mm:
            inner_parts.append(c)
        else:
            outer_parts.append(c)

    def dump(parts, suffix):
        merged = trimesh.util.concatenate(parts)
        out = CAD / f"{pn}_{suffix}.glb"
        merged.export(out)
        return out, len(parts), len(merged.vertices)

    out_in = dump(inner_parts, "inner")
    out_out = dump(outer_parts, "outer")
    info = {
        "pn": pn, "axis": axis, "r_split_mm": round(r_split_mm, 2),
        "r_range_mm": [round(r_lo, 1), round(r_hi, 1)],
        "n_components": len(comps),
        "inner": {"glb": str(out_in[0].relative_to(ROOT)), "n_comp": out_in[1], "n_verts": out_in[2]},
        "outer": {"glb": str(out_out[0].relative_to(ROOT)), "n_comp": out_out[1], "n_verts": out_out[2]},
    }
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pn")
    ap.add_argument("--axis", default="x", choices=["x", "y", "z"])
    ap.add_argument("--r-split", type=float, default=None)
    ap.add_argument("--rollers", default="inner", choices=["inner", "outer"])
    a = ap.parse_args()
    info = split_bearing(a.pn, a.axis, a.r_split, a.rollers)
    import json
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
