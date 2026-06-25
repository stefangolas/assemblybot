import json
from pathlib import Path
import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parent.parent
CAD = ROOT / "cad"

BODIES = {
    "clamp":   "CUSTOM-clamp.glb",
    "plate":   "CUSTOM-plate.glb",
    "subplate": "CUSTOM-subplate.glb",
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
    sec = m.section(plane_origin=[0, y, 0], plane_normal=[0, 1, 0])
    if sec is None:
        return []
    p2d, to3d = sec.to_planar()
    holes = []
    for loop in p2d.discrete:
        c = loop.mean(axis=0)
        r = np.linalg.norm(loop - c, axis=1).mean()
        w = trimesh.transformations.transform_points([[c[0], c[1], 0.0]], to3d)[0]
        holes.append((round(float(w[0]), 2), round(float(w[2]), 2), round(float(r), 2)))
    return sorted(holes)

def main():
    meshes = {}
    for name, fn in BODIES.items():
        p = CAD / fn
        if not p.exists():
            continue
        meshes[name] = m = as_mesh(p)
        report_bbox(name, m)

    print("-" * 78)
    for name in BODIES:
        m = meshes.get(name)
        if m is None: continue
        ymid = float(m.bounds[:, 1].mean())
        print(f"  [{name}] section y={ymid:.2f}:")
        for (x, z, r) in find_vert_holes(m, ymid):
            print(f"       hole @ x={x:8.2f} z={z:7.2f}  r={r:.2f}")

if __name__ == "__main__":
    main()
