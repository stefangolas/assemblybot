"""Measure the SL-TBLG split bodies (jaw + mounting plate) to (a) confirm the split
bodies share ONE frame and (b) locate the belt-clamp through-holes -- BEFORE authoring
any new ports. Read-only: prints measurements, writes nothing.

GLBs are metres (cascadio); we report millimetres. Holes are found by sectioning the
body with a horizontal (Y-normal) plane at mid-height and reporting small closed loops
(centroid + mean radius) -- the through-hole signatures.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parent.parent
CAD = ROOT / "cad"

BODIES = {
    "jaw":   "SL-TBLG_clamp_jaw.glb",
    "plate_split": "SL-TBLG_mounting_plate.glb",
    "plate_full":  "SL-TBLGS3M100-50-80-20-30-25-4.glb",
}


def as_mesh(path: Path) -> trimesh.Trimesh:
    s = trimesh.load(path, force="scene")
    m = trimesh.util.concatenate([g for g in s.geometry.values()])
    m.apply_scale(1000.0)  # metres -> mm
    return m


def report_bbox(name: str, m: trimesh.Trimesh):
    lo, hi = m.bounds
    print(f"  {name:12s} bbox mm  X[{lo[0]:8.2f},{hi[0]:8.2f}]  "
          f"Y[{lo[1]:7.2f},{hi[1]:7.2f}]  Z[{lo[2]:7.2f},{hi[2]:7.2f}]  "
          f"size=({hi[0]-lo[0]:.1f},{hi[1]-lo[1]:.1f},{hi[2]-lo[2]:.1f})")


def find_vert_holes(m: trimesh.Trimesh, y: float, rmax: float = 4.0):
    """Section with a Y-normal plane at height y; return small closed loops as
    (cx, cz, mean_radius_mm). These are vertical through-hole cross-sections."""
    sec = m.section(plane_origin=[0, y, 0], plane_normal=[0, 1, 0])
    if sec is None:
        return []
    p2d, to3d = sec.to_planar()
    holes = []
    for loop in p2d.discrete:                       # each closed polyline (u,v)
        c = loop.mean(axis=0)
        r = np.linalg.norm(loop - c, axis=1).mean()
        if r <= rmax:
            # map planar centroid back to world to recover (x,z)
            w = trimesh.transformations.transform_points([[c[0], c[1], 0.0]], to3d)[0]
            holes.append((round(float(w[0]), 2), round(float(w[2]), 2), round(float(r), 2)))
    return sorted(holes)


def main():
    print("=" * 78)
    print("SL-TBLG split-body measurement (mm). Are jaw + plate in ONE frame?")
    print("=" * 78)
    meshes = {}
    for name, fn in BODIES.items():
        p = CAD / fn
        if not p.exists():
            print(f"  {name}: MISSING {fn}")
            continue
        meshes[name] = m = as_mesh(p)
        report_bbox(name, m)

    print("-" * 78)
    print("Vertical (Y-axis) holes -- centroid (x, z) + mean radius, mid-height section:")
    for name in ("jaw", "plate_split", "plate_full"):
        m = meshes.get(name)
        if m is None:
            continue
        ymid = float(m.bounds[:, 1].mean())
        print(f"  [{name}] section y={ymid:.2f}:")
        for (x, z, r) in find_vert_holes(m, ymid):
            print(f"       hole @ x={x:8.2f} z={z:7.2f}  r={r:.2f}")


if __name__ == "__main__":
    main()
