"""Demonstrate the revolute/slider ENFORCE path (coaxial seat) in mate_solver.

A fasten pattern over-determines all 6 DOF (Kabsch). A pulley on an axle does NOT:
the joint pins the part onto an AXIS and leaves ONE DOF free -- spin (revolute) or
slide (slider). `enforce_coaxial_and_check` solves that 4-DOF seat and leaves the
on-axis DOF to the caller (spin_rad / along_mm). This proves, with NO render:

  * the seat puts the part's bore axis exactly ON the axle axis (enforce ~0);
  * the free DOF is REAL: spinning a revolute moves an off-axis rim point but
    leaves the axis invariant; sliding a slider translates along the axis;
  * a CHECK residual is evaluated at the solved pose just like the fasten path.

Run: PYTHONPATH=. python benchmarks/_coaxial_demo.py
"""
import numpy as np
from assembly.mate_solver import (enforce_coaxial_and_check, solve_coaxial,
                                  world_geom, xf_point)


class _Lib:
    """Minimal library: ref -> object with .feat(fid) -> geometry dict, matching
    the convention enforce_*_and_check expects (see mate_solver._local_geo)."""
    def __init__(self, parts): self._p = parts
    def __getitem__(self, ref): return self._p[ref]


class _Part:
    def __init__(self, feats): self._f = feats
    def feat(self, fid): return self._f[fid]


# --- the axle: a bracket holds a static shoulder-screw axle along world +X ------
AXLE_O = (-6.0, 12.5, 138.0)            # a point on the axle (world == bracket local)
AXLE_D = (1.0, 0.0, 0.0)               # axle runs along X
bracket = _Part({"axle": {"kind": "axis", "o": AXLE_O, "d": AXLE_D}})

# --- the idler pulley in its LOCAL frame: bore along local +Z, rim point off-axis
pulley = _Part({
    "bore": {"kind": "axis",  "o": (0.0, 0.0, 0.0), "d": (0.0, 0.0, 1.0)},
    "rim":  {"kind": "point", "p": (11.0, 0.0, 0.0)},   # 11 mm out from the bore
})

lib = _Lib({"brk": bracket, "pul": pulley})
placements = {"brk": {"R": [[1, 0, 0], [0, 1, 0], [0, 0, 1]], "t_mm": [0, 0, 0]}}


def seat(joint, spin_rad=0.0, along_mm=0.0):
    rep = enforce_coaxial_and_check(
        "pul", "pul.bore", "brk.axle",
        check_constraints=[("coaxial", "pul.bore", "brk.axle")],
        library=lib, placements=dict(placements),
        joint=joint, spin_rad=spin_rad, along_mm=along_mm)
    pose = rep.pose
    bore_w = world_geom(pulley.feat("bore"), pose)
    rim_w = xf_point(pose, pulley.feat("rim")["p"])
    return rep, bore_w, rim_w


print("Revolute/slider ENFORCE = seat coaxial to axle, on-axis DOF left free.\n")

# 1) revolute, no spin: bore lands ON the axle, rim is 11 mm off the axis line
rep0, bore0, rim0 = seat("revolute", spin_rad=0.0)
print(rep0.text())
assert rep0.enforce_rms_mm < 1e-6, "seat must put bore exactly on the axle"
assert rep0.ok, "coaxial check must be redundant-OK at the solved seat"

# 2) revolute, spin +90 deg: the FREE DOF. Axis must NOT move; rim MUST move.
rep90, bore90, rim90 = seat("revolute", spin_rad=np.pi / 2)
axis_shift = np.linalg.norm(np.asarray(bore90["o"]) - np.asarray(bore0["o"]))
# project axis origins onto the axle to compare the LINE, not the point param:
def _perp_off(o):
    w = np.asarray(o) - np.asarray(AXLE_O); d = np.asarray(AXLE_D, float)
    return np.linalg.norm(w - np.dot(w, d) * d)
rim_moved = np.linalg.norm(rim90 - rim0)
print(f"\n  spin +90 deg: rim point moved {rim_moved:6.2f} mm (free DOF is real);"
      f" bore still on axle (perp off {_perp_off(bore90['o']):.4f} mm)")
assert rep90.ok and rep90.enforce_rms_mm < 1e-6, "spun revolute is still coaxial"
assert rim_moved > 1.0, "spin must actually rotate an off-axis point"

# 3) slider, +20 mm along axis: the part translates ALONG the axle, still coaxial
repS, boreS, rimS = seat("slider", along_mm=20.0)
along = np.dot(np.asarray(boreS["o"]) - np.asarray(bore0["o"]), np.asarray(AXLE_D, float))
print(f"  slide +20 mm:  bore origin advanced {along:6.2f} mm along axle, "
      f"still coaxial ({'OK' if repS.ok else 'BROKEN'})")
assert repS.ok and abs(along - 20.0) < 1e-6, "slider must translate exactly along the axis"

print("\nOK: revolute/slider seats are coaxial (enforce ~0) AND leave the right DOF "
      "free.\nPulleys are now engine-SOLVED, not hand-placed.")
