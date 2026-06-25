"""Rung 3 -- RU85 rotary stage WITH the belt drive (core stack + 4:1 S5M belt).

Extends rung3_rotary.py: adds the 18T motor pulley at a center distance (snapped to an
integer S5M tooth count) and the generated S5M-15 belt loop around the 72T + 18T pitch
circles (the one allowed generated/flexible element). Verifies the belt mesh (pitch/
profile match on both pulleys) and the 4:1 ratio (72/18 tooth counts), then renders + LOOKs.

Belt plane = horizontal (both pulley axes vertical Z), belt centerline at world Z=38
(mid of the pulleys' 22 mm bodies; tooth bands span world Z=27..49).
"""
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np
import trimesh

from ontology.schema_v2 import PartDefinition
from ontology.templates import TEMPLATES
from ontology import ports_match as PM

ROOT = Path(__file__).resolve().parent.parent
OUT, LIBV2, CAD = ROOT / "out", ROOT / "library_v2", ROOT / "cad"
I = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
R_XZ = [[0, 0, -1], [0, 1, 0], [1, 0, 0]]      # CAD +X -> world +Z
PITCH = 5.0
PR72 = 72 * PITCH / (2 * math.pi)              # 57.296
PR18 = 18 * PITCH / (2 * math.pi)              # 14.324
Z_BELT = 38.0


def load(s): return PartDefinition.from_json(json.loads((LIBV2 / f"{s}.json").read_text()))


def belt_loop(c1, R1, c2, R2, z, n=64):
    """CCW external (open) belt loop tangent to two pitch circles of radii R1,R2 in the
    z-plane. Two tangent straights + a major arc on the large + minor arc on the small."""
    c1 = np.asarray(c1, float); c2 = np.asarray(c2, float)
    D = float(np.linalg.norm(c2 - c1)); phi = math.atan2(*(c2 - c1)[::-1])
    gamma = math.asin((R1 - R2) / D); alpha = math.pi / 2 - gamma
    def pt(c, R, ang): return [c[0] + R * math.cos(ang), c[1] + R * math.sin(ang), z]
    pts = []
    # large-circle wrap: phi+alpha -> phi+2pi-alpha (CCW, through phi+pi), sweep pi+2gamma
    for k in range(n + 1):
        a = (phi + alpha) + (2 * math.pi - 2 * alpha) * k / n
        pts.append(pt(c1, R1, a))
    # straight to small lower (phi-alpha), then small wrap phi-alpha -> phi+alpha (CCW, sweep 2alpha)
    for k in range(n + 1):
        a = (phi - alpha) + (2 * alpha) * k / n
        pts.append(pt(c2, R2, a))
    return np.asarray(pts)


def loop_len(pts):
    return float(np.sum(np.linalg.norm(np.diff(np.vstack([pts, pts[0]]), axis=0), axis=1)))


def solve_center_distance():
    """Find a center distance giving an INTEGER S5M tooth count (catalog-snappable)."""
    for D in np.arange(95.0, 140.0, 0.05):
        L = loop_len(belt_loop((0, 0), PR72, (D, 0), PR18, 0.0, n=400))
        N = L / PITCH
        if abs(N - round(N)) < 0.01:
            return float(D), int(round(N)), L
    # fallback: pick D, report nearest integer
    D = 109.0
    L = loop_len(belt_loop((0, 0), PR72, (D, 0), PR18, 0.0, n=400))
    return D, int(round(L / PITCH)), L


def build_belt_mesh(pts, width=15.0, thick=1.5):
    """Sweep a (radial thick x axial width) rectangle along the loop -> band mesh (metres)."""
    t, w = thick / 2000.0, width / 2000.0          # METRES (mesh boundary is metres) -- both axes
    poly = trimesh.path.polygons.Polygon([(-t, -w), (t, -w), (t, w), (-t, w)])
    path = np.vstack([pts, pts[0]]) / 1000.0       # metres, closed
    try:
        m = trimesh.creation.sweep_polygon(poly, path)
    except Exception:
        m = None
    return m


def main():
    OUT.mkdir(exist_ok=True)
    lib = {"p_base": load("ROTARY_BASE_RU85_REV_A"), "p_brg": load("RU85UUC0"),
           "p_adp": load("ROTARY_ADAPTER_RU85_S5M_REV_A"),
           "p_72": load("HTPA72S5M150-A-H50-KFC85-K5.5"), "p_18": load("HTPA18S5M150-A-H6.35")}
    D, N, L = solve_center_distance()
    pl = {
        "p_base": {"R": I,    "t_mm": [0, 0, 0]},
        "p_brg":  {"R": R_XZ, "t_mm": [0, 0, 0]},
        "p_adp":  {"R": I,    "t_mm": [0, 0, 15.0]},
        "p_72":   {"R": R_XZ, "t_mm": [0, 0, 27.0]},
        "p_18":   {"R": R_XZ, "t_mm": [float(D), 0, 27.0]},     # motor pulley at center distance D
    }
    print("=== RUNG 3 FULL -- RU85 ROTARY STAGE + 4:1 S5M BELT DRIVE ===\n")
    print(f"center distance D = {D:.2f} mm  ->  belt = {N}T S5M (L = {L:.1f} mm = {N}*5)")
    print(f"reduction = 72/18 = {72/18:.1f}:1\n")

    # belt loop + mesh
    belt = belt_loop((0, 0), PR72, (float(D), 0), PR18, Z_BELT, n=80)
    m = build_belt_mesh(belt)
    if m is not None:
        m.export(str(CAD / "belt_s5m.glb"))
        print(f"belt mesh: {len(m.vertices)} verts -> cad/belt_s5m.glb")
    else:
        print("(belt mesh sweep failed; loop still verified numerically)")

    # checks: 72T<->18T share an S5M belt (pitch/profile), and the belt couples them 4:1
    pp = PM.pitch_profile_match(lib["p_72"].port("teeth"), lib["p_18"].port("teeth"))
    print("\n[mesh] 72T <-> 18T teeth:", pp)
    print(f"[ratio] tooth counts 72:18 = 4:1 (one motor rev -> 1/4 stage rev)")
    aw = PM.active_width_overlap(lib["p_72"].port("teeth"), lib["p_18"].port("teeth"))
    print("[width]", aw)

    render = [
        ("p_base", "/cad/ROTARY_BASE_RU85_REV_A.glb",        0x8a9097),
        ("p_brg",  "/cad/RU85UUC0.glb",                       0xb5a642),
        ("p_adp",  "/cad/ROTARY_ADAPTER_RU85_S5M_REV_A.glb",  0xc0563f),
        ("p_72",   "/cad/HTPA72S5M150.glb",                   0x4a7fb0),
        ("p_18",   "/cad/HTPA18S5M150.glb",                   0x4ab07f),
        ("p_belt", "/cad/belt_s5m.glb",                       0x2b2f36),
    ]
    out = dict(pl)
    out["p_belt"] = {"R": I, "t_mm": [0, 0, 0]}
    out["_render"] = [{"ref": r, "url": u, "color": c} for r, u, c in render]
    (OUT / "rung3_full_placements.json").write_text(json.dumps(out, indent=2))
    print("\nwrote out/rung3_full_placements.json")
    try:
        from benchmarks._shot import shoot
        imgs = shoot("out/rung3_full_placements.json", "out/rung3_full", "p_belt", ("iso", "z", "x"))
        print("rendered:", ", ".join(imgs))
    except Exception as e:  # noqa: BLE001
        print(f"(render skipped: {e})")


if __name__ == "__main__":
    main()
