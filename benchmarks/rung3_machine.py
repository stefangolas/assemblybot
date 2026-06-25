"""Rung 3 -- the COMPLETE machine LOOK: 40 mm T-slot frame + the full rotary stage.

Adds the stationary 220 mm-square frame (4x 6575N203 40 mm extrusion, member centerlines
X=+-90, Y=+-90) under the base, so the whole load path is grounded to a real frame:
tabletop -> pulley -> adapter -> inner ring -[RU85]- outer ring -> base -> frame -> ground.
(Base anchors via 8x M6 SHCS into M6 drop-in T-nuts in the frame slots -- a quick warm-tab
McMaster fetch, noted; the structural members + base are modeled here.)
"""
from __future__ import annotations
import json
from pathlib import Path
from benchmarks.rung3_redesign import I, R_XZ, PR72, PR18, Z_BELT, solve_center_distance, OUT
from benchmarks.rung3_full import belt_loop, build_belt_mesh, CAD

# 6575N203: 40x40x304.8, length along local Z. R_EXT -> length to world X; R_EY -> length to world Y.
R_EXT = [[0, 0, 1], [0, 1, 0], [-1, 0, 0]]
R_EY = [[1, 0, 0], [0, 0, 1], [0, -1, 0]]
TOP_UNDER_Z = 52.0


def main():
    OUT.mkdir(exist_ok=True)
    D, N, L = solve_center_distance()
    belt = belt_loop((0, 0), PR72, (float(D), 0), PR18, Z_BELT, n=80)
    m = build_belt_mesh(belt)
    if m is not None:
        m.export(str(CAD / "belt_s5m.glb"))
    pl = {
        # stationary 40mm frame: top face at Z=-15 (base bottom), members Z=-55..-15
        "p_frX1": {"R": R_EXT, "t_mm": [0, 90, -35]},     # X-rail @ Y=+90
        "p_frX2": {"R": R_EXT, "t_mm": [0, -90, -35]},    # X-rail @ Y=-90
        "p_frY1": {"R": R_EY,  "t_mm": [90, 0, -35]},     # Y-rail @ X=+90
        "p_frY2": {"R": R_EY,  "t_mm": [-90, 0, -35]},    # Y-rail @ X=-90
        # the rotary stage (redesigned: tabletop on the pulley hub, clear of the belt)
        "p_base": {"R": I,    "t_mm": [0, 0, 0]},
        "p_brg":  {"R": R_XZ, "t_mm": [0, 0, 0]},
        "p_adp":  {"R": I,    "t_mm": [0, 0, 15.0]},
        "p_72":   {"R": R_XZ, "t_mm": [0, 0, 27.0]},
        "p_18":   {"R": R_XZ, "t_mm": [float(D), 0, 27.0]},
        "p_belt": {"R": I,    "t_mm": [0, 0, 0]},
        "p_top":  {"R": I,    "t_mm": [0, 0, TOP_UNDER_Z]},
    }
    render = [
        ("p_frX1", "/cad/6575N203.glb", 0x5f6a72), ("p_frX2", "/cad/6575N203.glb", 0x5f6a72),
        ("p_frY1", "/cad/6575N203.glb", 0x5f6a72), ("p_frY2", "/cad/6575N203.glb", 0x5f6a72),
        ("p_base", "/cad/ROTARY_BASE_RU85_REV_A.glb", 0x8a9097),
        ("p_brg",  "/cad/RU85UUC0.glb", 0xb5a642),
        ("p_adp",  "/cad/ROTARY_ADAPTER_RU85_S5M_REV_A.glb", 0xc0563f),
        ("p_72",   "/cad/HTPA72S5M150.glb", 0x4a7fb0),
        ("p_18",   "/cad/HTPA18S5M150.glb", 0x4ab07f),
        ("p_belt", "/cad/belt_s5m.glb", 0x2b2f36),
        ("p_top",  "/cad/A6061-tabletop.glb", 0xd9c16a),
    ]
    out = dict(pl)
    out["_render"] = [{"ref": r, "url": u, "color": c} for r, u, c in render]
    (OUT / "rung3_machine_placements.json").write_text(json.dumps(out, indent=2))
    print(f"complete machine: frame (4x 6575N203) + rotary stage; belt {N}T 4:1")
    print("wrote out/rung3_machine_placements.json")
    try:
        from benchmarks._shot import shoot
        shoot("out/rung3_machine_placements.json", "out/rung3_machine", "", ("iso", "x"))
        print("rendered out/rung3_machine_{iso,x}.png")
    except Exception as e:  # noqa: BLE001
        print(f"(render skipped: {e})")


if __name__ == "__main__":
    main()
