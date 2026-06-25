"""Measure the reconfigured FALBS-...-H40-M4-NA5 bracket BEFORE re-authoring ports.
Read-only: converts STEP->glb (cascadio, metres), loads in mm, prints bbox + holes.

Axle hole: axis along Z (through the vertical leg near top). Foot holes: axis along Y
(through the base plate at Y~0). We section with planes normal to each axis and report
small closed loops (centroid + mean radius) = through-hole signatures.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh
import cascadio

ROOT = Path(__file__).resolve().parent.parent
CAD = ROOT / "cad"
STP = CAD / "_falbsM4_extract" / "FALBS-SP-T3.2-A80-B30-L30-H40-M4-NA5.stp"
GLB = CAD / "FALBS-SP-T3.2-A80-B30-L30-H40-M4-NA5.glb"


def as_mesh(path: Path) -> trimesh.Trimesh:
    s = trimesh.load(path, force="scene")
    m = trimesh.util.concatenate([g for g in s.geometry.values()])
    m.apply_scale(1000.0)  # cascadio metres -> mm
    return m


def holes_along(m, axis, coord, rmax=5.0):
    """Section with a plane normal to `axis` (0=X,1=Y,2=Z) at value `coord`.
    Return small closed loops as (a,b,r) in the other two world coords + mean radius."""
    n = [0, 0, 0]; n[axis] = 1
    o = [0, 0, 0]; o[axis] = coord
    sec = m.section(plane_origin=o, plane_normal=n)
    if sec is None:
        return []
    p2d, to3d = sec.to_planar()
    out = []
    for loop in p2d.discrete:
        c = loop.mean(axis=0)
        r = np.linalg.norm(loop - c, axis=1).mean()
        if r <= rmax:
            w = trimesh.transformations.transform_points([[c[0], c[1], 0.0]], to3d)[0]
            others = [round(float(w[i]), 2) for i in range(3) if i != axis]
            out.append((others[0], others[1], round(float(r), 2)))
    return sorted(out)


def main():
    if not GLB.exists():
        print(f"converting {STP.name} -> {GLB.name}")
        cascadio.step_to_glb(str(STP), str(GLB))
    m = as_mesh(GLB)
    lo, hi = m.bounds
    print("=" * 78)
    print(f"FALBS-...-H40-M4-NA5  bbox mm  "
          f"X[{lo[0]:.2f},{hi[0]:.2f}] Y[{lo[1]:.2f},{hi[1]:.2f}] Z[{lo[2]:.2f},{hi[2]:.2f}]  "
          f"size=({hi[0]-lo[0]:.1f},{hi[1]-lo[1]:.1f},{hi[2]-lo[2]:.1f})")
    print("=" * 78)

    # Find where the vertical leg slab sits in Z by scanning sections.
    print("\n[scan] Z sections (axle axis ~ along Z); leg is a ~3.2mm slab:")
    for zc in (1.0, 1.6, 2.0, 3.0, 5.0, 10.0, 15.0):
        hs = holes_along(m, 2, zc)
        if hs:
            print(f"   z={zc:5.2f}: " + "  ".join(f"(x={a},y={b},dia={2*r:.2f})" for a, b, r in hs))

    # FOOT holes: axis along Y, base plate near Y=lo. Scan a few heights.
    print("\n[foot] Y sections near base (foot axis ~ along Y) -> (x, z, dia):")
    for yc in (0.8, 1.6, 2.4):
        hs = holes_along(m, 1, yc)
        if hs:
            print(f"   y={yc:4.2f}: " + "  ".join(f"(x={a},z={b},dia={2*r:.2f})" for a, b, r in hs))


if __name__ == "__main__":
    main()
