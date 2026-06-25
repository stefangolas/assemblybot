"""Rung 3 -- COMPLETE rotary stage: core stack + 4:1 belt drive + 4 standoffs + tabletop.

Adds the output side (4x SCB6-30 M6 standoffs on the adapter -> 200x200 tabletop) to the
verified core+drive, renders the whole machine, and runs verification #8 (do the rotating
standoffs clear the belt through 360 deg?) as an honest swept-clearance check.
"""
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np

from benchmarks.rung3_full import (load, belt_loop, build_belt_mesh, solve_center_distance,
                                    I, R_XZ, PR72, PR18, Z_BELT, OUT, CAD)

STANDOFF_XY = [(55, 55), (-55, 55), (-55, -55), (55, -55)]


def main():
    OUT.mkdir(exist_ok=True)
    D, N, L = solve_center_distance()
    # core + drive placements
    pl = {
        "p_base": {"R": I,    "t_mm": [0, 0, 0]},
        "p_brg":  {"R": R_XZ, "t_mm": [0, 0, 0]},
        "p_adp":  {"R": I,    "t_mm": [0, 0, 15.0]},
        "p_72":   {"R": R_XZ, "t_mm": [0, 0, 27.0]},
        "p_18":   {"R": R_XZ, "t_mm": [float(D), 0, 27.0]},
    }
    # belt
    belt = belt_loop((0, 0), PR72, (float(D), 0), PR18, Z_BELT, n=80)
    m = build_belt_mesh(belt)
    if m is not None:
        m.export(str(CAD / "belt_s5m.glb"))
    # 4 standoffs: SCB6-30 long axis X (0..36): stud X0..6 down into adapter, body X6..36.
    # R_XZ maps X->+Z; t_z=21 puts body bottom (X=6) at Z=27 (adapter top), female top (X=36) at Z=57.
    for i, (x, y) in enumerate(STANDOFF_XY, 1):
        pl[f"p_so{i}"] = {"R": R_XZ, "t_mm": [float(x), float(y), 21.0]}
    # tabletop: bottom Z=0/top Z=10 in its frame -> seat on standoff tops (Z=57)
    pl["p_top"] = {"R": I, "t_mm": [0, 0, 57.0]}

    print("=== RUNG 3 COMPLETE -- full rotary stage ===")
    print(f"belt {N}T S5M, 4:1; standoffs SCB6-30 (body Z=27..57); tabletop 200x200 @ Z=57..67\n")

    # verification #8: rotating standoffs (swept circle R=55*sqrt2) vs the belt band (at Z_BELT,
    # band half-width 7.5). The output (adapter+pulley+standoffs+tabletop) ROTATES; the belt run
    # to the motor is fixed. Does any belt point fall inside the standoff swept annulus at the
    # belt's Z? standoff body radius ~5 mm, so swept ring is R in [R_so-5, R_so+5].
    R_so = math.hypot(55, 55)
    so_lo, so_hi = R_so - 5.0, R_so + 5.0
    # CLOSE the loop and DENSELY resample (~1 mm) so the STRAIGHT tangent runs are sampled --
    # the arc-only points miss the runs and give a FALSE pass (the runs are what cross R~78).
    closed = np.vstack([belt, belt[0]])
    dense = []
    for a, b in zip(closed[:-1], closed[1:]):
        k = max(2, int(np.linalg.norm(b - a)))
        for t in np.linspace(0, 1, k, endpoint=False):
            dense.append(a + (b - a) * t)
    dense = np.asarray(dense)
    R_belt = np.hypot(dense[:, 0], dense[:, 1])
    hits = int(np.sum((R_belt >= so_lo) & (R_belt <= so_hi)))
    rmin, rmax = float(R_belt.min()), float(R_belt.max())
    print(f"[#8] standoff swept ring R in [{so_lo:.1f}, {so_hi:.1f}] mm at Z={Z_BELT}")
    print(f"     belt radial extent R in [{rmin:.1f}, {rmax:.1f}] mm; belt points within the swept ring: {hits}")
    if hits > 0:
        print("     -> FAIL #8: the rotating standoffs WOULD strike the belt run "
              "(belt crosses the standoff swept circle at the belt's height).")
        print("     FIX options: raise the tabletop above the belt (longer standoffs so their")
        print("     BODY clears Z>45.5), or route the belt below the adapter, or shrink the drive.")
    else:
        print("     -> PASS #8: belt stays clear of the standoff swept ring.")

    render = [
        ("p_base", "/cad/ROTARY_BASE_RU85_REV_A.glb",        0x8a9097),
        ("p_brg",  "/cad/RU85UUC0.glb",                       0xb5a642),
        ("p_adp",  "/cad/ROTARY_ADAPTER_RU85_S5M_REV_A.glb",  0xc0563f),
        ("p_72",   "/cad/HTPA72S5M150.glb",                   0x4a7fb0),
        ("p_18",   "/cad/HTPA18S5M150.glb",                   0x4ab07f),
        ("p_belt", "/cad/belt_s5m.glb",                       0x2b2f36),
        ("p_so1",  "/cad/SCB6-30.glb",                        0xcfcfcf),
        ("p_so2",  "/cad/SCB6-30.glb",                        0xcfcfcf),
        ("p_so3",  "/cad/SCB6-30.glb",                        0xcfcfcf),
        ("p_so4",  "/cad/SCB6-30.glb",                        0xcfcfcf),
        ("p_top",  "/cad/A6061-tabletop.glb",                 0xd9c16a),
    ]
    out = dict(pl)
    out["p_belt"] = {"R": I, "t_mm": [0, 0, 0]}
    out["_render"] = [{"ref": r, "url": u, "color": c} for r, u, c in render]
    (OUT / "rung3_complete_placements.json").write_text(json.dumps(out, indent=2))
    print("\nwrote out/rung3_complete_placements.json")
    try:
        from benchmarks._shot import shoot
        imgs = shoot("out/rung3_complete_placements.json", "out/rung3_complete", "", ("iso", "x", "z"))
        print("rendered:", ", ".join(imgs))
    except Exception as e:  # noqa: BLE001
        print(f"(render skipped: {e})")


if __name__ == "__main__":
    main()
