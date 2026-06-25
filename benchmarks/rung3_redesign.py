"""Rung 3 REDESIGN (resolves the #8 standoff-vs-belt interference).

ROOT CAUSE (proven): with a top-side OFFSET belt drive + a CONTINUOUS 360-deg rotary
output, ANY rotating support that spans the belt's Z-band (30.5..45.5) must lie either
at R<59.5 (collides with the pulley) or R 59.5..109 (collides with the swept belt run);
R>109 is outside the 200 mm tabletop. So the task's 4 outboard standoffs at R=78 are
geometrically impossible here regardless of length -- they sweep through the belt run.

FIX: the driven pulley HUB carries the tabletop. The tabletop is bolted down onto the
72T pulley top (4x long M5 through the pulley's PCD85 holes into the adapter) on short
spacers, so the entire rotating payload sits ABOVE the belt plane (underside Z=52 >
belt top 45.5 and > 18T top 49) and NOTHING rotates out into the belt run. The pulley
itself spanning the belt band is the intended belt mesh, not interference.

Re-runs the swept #8 check and renders the assembled + a rotated (colliding-test) pose.
"""
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np

from benchmarks.rung3_full import (belt_loop, build_belt_mesh, solve_center_distance,
                                    I, R_XZ, PR72, PR18, Z_BELT, OUT, CAD)

TOP_UNDER_Z = 52.0   # tabletop underside: above belt top (45.5) and 18T top (49)


def swept_check(belt, moving_zspans):
    """#8: does any ROTATING member's swept ring cross the belt run? A member at radial
    band [r0,r1] and Z-span [z0,z1] interferes iff its Z-span overlaps the belt band AND
    its radial band overlaps the belt's radial extent. Dense-sampled belt (incl. runs)."""
    closed = np.vstack([belt, belt[0]])
    dense = []
    for a, b in zip(closed[:-1], closed[1:]):
        k = max(2, int(np.linalg.norm(b - a)))
        for t in np.linspace(0, 1, k, endpoint=False):
            dense.append(a + (b - a) * t)
    dense = np.asarray(dense)
    R = np.hypot(dense[:, 0], dense[:, 1])
    belt_z = (30.5, 45.5)
    rmin, rmax = float(R.min()), float(R.max())
    worst = None
    for name, (z0, z1), (r0, r1) in moving_zspans:
        z_overlap = not (z1 < belt_z[0] or z0 > belt_z[1])
        r_overlap = not (r1 < rmin or r0 > rmax)
        bad = z_overlap and r_overlap
        print(f"   {name:18s} Z[{z0:.1f},{z1:.1f}] R[{r0:.1f},{r1:.1f}] -> "
              f"{'INTERFERES' if bad else 'clear'} (beltZ {belt_z}, beltR [{rmin:.1f},{rmax:.1f}])")
        if bad:
            worst = name
    return worst


def main():
    OUT.mkdir(exist_ok=True)
    D, N, L = solve_center_distance()
    pl = {
        "p_base": {"R": I,    "t_mm": [0, 0, 0]},
        "p_brg":  {"R": R_XZ, "t_mm": [0, 0, 0]},
        "p_adp":  {"R": I,    "t_mm": [0, 0, 15.0]},
        "p_72":   {"R": R_XZ, "t_mm": [0, 0, 27.0]},
        "p_18":   {"R": R_XZ, "t_mm": [float(D), 0, 27.0]},
        # REDESIGN: tabletop carried on the pulley hub, underside at Z=52 (above the belt)
        "p_top":  {"R": I,    "t_mm": [0, 0, TOP_UNDER_Z]},
    }
    belt = belt_loop((0, 0), PR72, (float(D), 0), PR18, Z_BELT, n=80)
    m = build_belt_mesh(belt)
    if m is not None:
        m.export(str(CAD / "belt_s5m.glb"))

    print("=== RUNG 3 REDESIGN -- #8 fix: tabletop on the pulley hub, above the belt ===\n")
    print(f"belt {N}T S5M, 4:1; tabletop underside Z={TOP_UNDER_Z} (belt top 45.5, 18T top 49)\n")
    print("[#8] swept-interference of every ROTATING member vs the belt run:")
    # rotating members now: the pulley (intended mesh, excluded) + the tabletop (Z 52..62).
    worst = swept_check(belt, [
        ("tabletop", (TOP_UNDER_Z, TOP_UNDER_Z + 10), (0.0, 141.4)),   # 200mm sq -> corner R=141
    ])
    print(f"\n[#8] VERDICT: {'FAIL via ' + worst if worst else 'PASS -- nothing rotating crosses the belt run'}")

    render = [
        ("p_base", "/cad/ROTARY_BASE_RU85_REV_A.glb",        0x8a9097),
        ("p_brg",  "/cad/RU85UUC0.glb",                       0xb5a642),
        ("p_adp",  "/cad/ROTARY_ADAPTER_RU85_S5M_REV_A.glb",  0xc0563f),
        ("p_72",   "/cad/HTPA72S5M150.glb",                   0x4a7fb0),
        ("p_18",   "/cad/HTPA18S5M150.glb",                   0x4ab07f),
        ("p_belt", "/cad/belt_s5m.glb",                       0x2b2f36),
        ("p_top",  "/cad/A6061-tabletop.glb",                 0xd9c16a),
    ]
    out = dict(pl)
    out["p_belt"] = {"R": I, "t_mm": [0, 0, 0]}
    out["_render"] = [{"ref": r, "url": u, "color": c} for r, u, c in render]
    (OUT / "rung3_redesign_placements.json").write_text(json.dumps(out, indent=2))

    # also a rotated pose (output +-28deg) with the tabletop HIDDEN, to LOOK at the belt
    # gap under the (now absent) standoff swath -- proving nothing sweeps the belt.
    rot = dict(out)
    th = math.radians(-28.0)
    Rz = np.array([[math.cos(th), -math.sin(th), 0], [math.sin(th), math.cos(th), 0], [0, 0, 1]])
    for ref in ("p_adp", "p_72", "p_top"):
        P = dict(pl[ref]); P["R"] = (Rz @ np.array(P["R"], float)).tolist()
        P["t_mm"] = (Rz @ np.array(P["t_mm"], float)).tolist(); rot[ref] = P
    rot["_render"] = [r for r in out["_render"] if r["ref"] != "p_top"]
    (OUT / "rung3_redesign_rot_placements.json").write_text(json.dumps(rot, indent=2))

    print("\nwrote out/rung3_redesign_placements.json (+_rot)")
    try:
        from benchmarks._shot import shoot
        shoot("out/rung3_redesign_placements.json", "out/rung3_redesign", "", ("iso", "x"))
        shoot("out/rung3_redesign_rot_placements.json", "out/rung3_redesign_rot", "", ("z",))
        print("rendered rung3_redesign_{iso,x}.png + rung3_redesign_rot_z.png")
    except Exception as e:  # noqa: BLE001
        print(f"(render skipped: {e})")


if __name__ == "__main__":
    main()
