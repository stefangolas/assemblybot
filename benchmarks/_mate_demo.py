"""Demonstrate the ENFORCE/CHECK constraint engine on the belt clamp.

Shows, programmatically (no render): the 4-screw fasten ENFORCES the clamp pose,
but a symmetric hole pattern leaves a 4-fold rotation ambiguity -- so the fasten
ALONE cannot tell a correctly-meshed clamp from one rotated 90 deg. The CHECK
constraints decide it: coplanar(faces) is satisfied by BOTH (both lie flat on the
belt), but the TOOTH-DIRECTION (parallel) check is satisfied only by the correct
orientation. That parallel-direction term is how 'the teeth enforce a constraint'
-- the thing the bare coincident anchor missed.

Run: PYTHONPATH=. python benchmarks/_mate_demo.py
"""
import numpy as np
from assembly.mate_solver import solve_rigid, world_geom, residual, pitch_match, xf_point

# --- carriage (the 'sliding plate'): 4x M2 @ 10x10 on its top face (WORLD) -----
CARR_TOP_Y = 21.4
carr_holes_world = [(5, CARR_TOP_Y, 5), (5, CARR_TOP_Y, -5),
                    (-5, CARR_TOP_Y, 5), (-5, CARR_TOP_Y, -5)]

# --- belt lower run toothed face (WORLD): teeth face UP, ridges run along X -----
BELT_PITCH = 2.0
belt_face = {"kind": "plane", "o": (0, CARR_TOP_Y, 0), "n": (0, 1, 0)}      # teeth up
belt_tooth_dir = {"kind": "axis", "o": (0, CARR_TOP_Y, 0), "d": (1, 0, 0)}  # ridges along X

# --- clamp TBCN2-6 in its LOCAL frame ------------------------------------------
# 4 screw holes on the bottom face (local y=0), screw axis local +Y;
# toothed grip on the bottom face (normal local -Y), ridges along local X.
clamp_holes_local = [(5, 0, 5), (5, 0, -5), (-5, 0, 5), (-5, 0, -5)]
clamp_grip_local  = {"kind": "plane", "o": (0, 0, 0), "n": (0, -1, 0)}
clamp_tooth_local = {"kind": "axis",  "o": (0, 0, 0), "d": (1, 0, 0)}
CLAMP_PITCH = 2.0


def evaluate(pose, label):
    grip = world_geom(clamp_grip_local, pose)
    tdir = world_geom(clamp_tooth_local, pose)
    # enforce residual: each screw hole lands on SOME carriage hole (set match --
    # a symmetric pattern fits in several rotations, which is the whole point).
    W = np.asarray(carr_holes_world, float)
    rms = float(np.sqrt(np.mean([min(np.sum((xf_point(pose, h) - W)**2, axis=1))
                                 for h in clamp_holes_local])))
    checks = [
        residual("coplanar", grip, belt_face, "clamp.grip", "belt.tooth_face"),
        residual("parallel", tdir, belt_tooth_dir, "clamp.tooth_dir", "belt.tooth_dir"),
        pitch_match("clamp.pitch", CLAMP_PITCH, "belt.pitch", BELT_PITCH),
    ]
    print(f"\n=== {label} ===")
    print(f"  ENFORCE fasten (4 screws): hole-pattern RMS = {rms:.3f} mm "
          f"({'holes match' if rms < 0.1 else 'HOLES DO NOT MATCH'})")
    allok = True
    for c in checks:
        ok = c.satisfied()
        allok &= ok
        print(f"  CHECK {c.ctype:9s}: {c.detail:42s} -> "
              f"{'REDUNDANT-OK' if ok else 'VIOLATED'}")
    print(f"  RESULT: {'clamp correctly meshed' if allok else 'MESH INVALID'}")
    return allok


# pose A: solved straight from the holes (correct orientation)
poseA = solve_rigid(clamp_holes_local, carr_holes_world)
# pose B: rotate the clamp 90 deg about the bolt axis (world Y) THROUGH the hole-
# pattern centroid. The 4-fold-symmetric pattern maps onto itself, so the screws
# still fit (RMS ~ 0) -- but the teeth now run crossways.
Ry90 = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], float)
c = np.array([0, CARR_TOP_Y, 0], float)                    # pattern centroid
RA, tA = np.asarray(poseA["R"]), np.asarray(poseA["t_mm"])
poseB = {"R": (Ry90 @ RA).tolist(), "t_mm": (Ry90 @ tA + (c - Ry90 @ c)).tolist()}

print("Belt clamp -> carriage: fasten ENFORCES pose; teeth CHECK meshing.")
okA = evaluate(poseA, "clamp as-meshed (correct)")
okB = evaluate(poseB, "clamp rotated 90 deg (the bug) -- same screws, fits holes")
print("\nThe fastener fits BOTH (symmetric pattern). Only the tooth-direction")
print("CHECK separates them: A passes, B is caught WITHOUT a render.")
assert okA and not okB, "engine should accept A and reject B"
print("OK: engine accepts correct mesh, rejects the 90deg-off clamp.")
