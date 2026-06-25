"""Constraint engine: ENFORCE vs CHECK (Section 4c/4d, programmatic).

The manual's constraints are geometry, not labels. This module makes them bite:

  * a part's pose is SOLVED from the subset of constraints tagged `enforce`
    (e.g. the 4-screw fasten pattern fully locates the belt clamp on the
    carriage -- 4 hole axes + a seated face over-determine the rigid transform);
  * every other constraint tagged `check` is then EVALUATED as a geometric
    residual at that solved pose and reported as redundant-consistent (residual
    ~ 0, the healthy over-constraint a real bolted joint always has) or violated.

So "the belt teeth also constrain the clamp" is not prompt-enforced hand-waving:
we set the fasten, solve the pose, and the belt-tooth coplanarity is CHECKED to
fall out of it within tolerance. If the clamp were 90 deg off (the bug), the
checked tooth-mate residual is large and the engine says so -- no render needed.

Features carry geometry in their PART-LOCAL frame; the part placement {R,t_mm}
carries them to world. One source of pose (the solved placement) feeds both this
engine and the viewer, exactly as Section 3 requires.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# ---- geometry: local feature -> world via a placement ----------------------

def _R(p):  return np.asarray(p["R"], float)
def _t(p):  return np.asarray(p["t_mm"], float)


def xf_point(p, v):   return _R(p) @ np.asarray(v, float) + _t(p)
def xf_dir(p, v):     return _R(p) @ np.asarray(v, float)


def world_geom(feat_geo: dict, place: dict) -> dict:
    """Transform a local feature {kind, ...} into world coordinates.
    kinds: 'point'{p}, 'axis'{o,d}, 'plane'{o,n}."""
    k = feat_geo["kind"]
    if k == "point":
        return {"kind": "point", "p": xf_point(place, feat_geo["p"])}
    if k == "axis":
        return {"kind": "axis", "o": xf_point(place, feat_geo["o"]),
                "d": xf_dir(place, feat_geo["d"])}
    if k == "plane":
        return {"kind": "plane", "o": xf_point(place, feat_geo["o"]),
                "n": xf_dir(place, feat_geo["n"])}
    raise ValueError(f"unknown feature kind {k!r}")


# ---- residuals: how badly is a constraint violated, in mm + rad -------------

def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def _line_line_dist(o1, d1, o2, d2) -> float:
    d1, d2 = _unit(d1), _unit(d2)
    n = np.cross(d1, d2)
    nn = np.linalg.norm(n)
    w = np.asarray(o1) - np.asarray(o2)
    if nn < 1e-9:                                   # parallel
        return float(np.linalg.norm(w - np.dot(w, d1) * d1))
    return float(abs(np.dot(w, n)) / nn)


@dataclass
class Residual:
    ctype: str
    a: str
    b: str
    pos_mm: float          # positional error (mm)
    ang_rad: float         # orientation error (rad)
    detail: str

    def satisfied(self, pos_tol=0.6, ang_tol=0.05) -> bool:
        return self.pos_mm <= pos_tol and self.ang_rad <= ang_tol


def residual(ctype: str, A: dict, B: dict, a="", b="") -> Residual:
    """Geometric residual of one constraint between two WORLD features."""
    if ctype == "coincident":
        pa = A["p"] if A["kind"] == "point" else A.get("o")
        pb = B["p"] if B["kind"] == "point" else B.get("o")
        d = float(np.linalg.norm(np.asarray(pa) - np.asarray(pb)))
        return Residual(ctype, a, b, d, 0.0, f"point gap {d:.3f} mm")
    if ctype == "coaxial":
        ang = float(np.arccos(np.clip(abs(np.dot(_unit(A["d"]), _unit(B["d"]))), -1, 1)))
        dist = _line_line_dist(A["o"], A["d"], B["o"], B["d"])
        return Residual(ctype, a, b, dist, ang,
                        f"axis offset {dist:.3f} mm, tilt {np.degrees(ang):.2f} deg")
    if ctype == "coplanar":
        na, nb = _unit(A["n"]), _unit(B["n"])
        ang = float(np.arccos(np.clip(abs(np.dot(na, nb)), -1, 1)))  # parallel OR anti
        gap = float(abs(np.dot(np.asarray(A["o"]) - np.asarray(B["o"]), na)))
        return Residual(ctype, a, b, gap, ang,
                        f"plane offset {gap:.3f} mm, normal tilt {np.degrees(ang):.2f} deg")
    if ctype == "parallel":
        # two direction vectors (axes); pos error is meaningless, only angle.
        # This is the TOOTH-DIRECTION term: clamp groove ridge // belt tooth ridge.
        da, db = _unit(A["d"]), _unit(B["d"])
        ang = float(np.arccos(np.clip(abs(np.dot(da, db)), -1, 1)))
        return Residual(ctype, a, b, 0.0, ang, f"direction tilt {np.degrees(ang):.2f} deg")
    raise ValueError(f"residual: unsupported constraint {ctype!r}")


def pitch_match(name_a: str, pitch_a: float, name_b: str, pitch_b: float,
                tol=1e-3) -> Residual:
    """Scalar tooth-pitch compatibility -- a toothed pair only meshes if pitches
    are equal (belt pitch == clamp groove pitch == pulley pitch). Modeled as a
    `distance`-style residual on the pitch parameters, NOT per-tooth geometry."""
    d = abs(pitch_a - pitch_b)
    return Residual("pitch", name_a, name_b, d, 0.0,
                    f"pitch {pitch_a} vs {pitch_b} mm (|d|={d:.3f})")


# ---- ENFORCE: solve a rigid pose from matched point pairs (Kabsch) ----------

def solve_rigid(local_pts, world_pts) -> dict:
    """Least-squares rigid transform (R,t), no scale, mapping local->world for the
    matched point sets (>=3 non-collinear pairs). This is how a bolt PATTERN
    locates a part: the hole centres are the matched points."""
    P = np.asarray(local_pts, float)
    Q = np.asarray(world_pts, float)
    cP, cQ = P.mean(0), Q.mean(0)
    H = (P - cP).T @ (Q - cQ)
    U, _, Vt = np.linalg.svd(H)
    D = np.eye(3)
    D[2, 2] = np.sign(np.linalg.det(Vt.T @ U.T))      # reflection guard
    R = Vt.T @ D @ U.T
    t = cQ - R @ cP
    return {"R": R.tolist(), "t_mm": t.tolist()}


def solve_pattern_on_plane(local_pts, world_pts, local_plane, world_plane) -> dict:
    """Least-squares rigid transform for a bolt pattern, subject to the hard constraint
    that local_plane exactly opposes world_plane (n_world = -R * n_local) and their
    origins are coincident along the normal. Solves X, Y, and Yaw from the points."""
    ln = _unit(np.asarray(local_plane["n"], float))
    wn = _unit(np.asarray(world_plane["n"], float))
    R_align = _rot_align(ln, -wn)

    lo = np.asarray(local_plane["o"], float)
    wo = np.asarray(world_plane["o"], float)

    Z = wn
    u = np.array([1.0, 0.0, 0.0])
    if abs(np.dot(u, Z)) > 0.9:
        u = np.array([0.0, 1.0, 0.0])
    X = _unit(np.cross(u, Z))
    Y = np.cross(Z, X)

    L_pts_2d, W_pts_2d = [], []
    for lp, wp in zip(local_pts, world_pts):
        lp_world_aligned = R_align @ (np.asarray(lp) - lo)
        L_pts_2d.append([np.dot(lp_world_aligned, X), np.dot(lp_world_aligned, Y)])
        wp_rel = np.asarray(wp) - wo
        W_pts_2d.append([np.dot(wp_rel, X), np.dot(wp_rel, Y)])

    P, Q = np.asarray(L_pts_2d, float), np.asarray(W_pts_2d, float)
    cP, cQ = P.mean(0), Q.mean(0)
    H = (P - cP).T @ (Q - cQ)
    U, _, Vt = np.linalg.svd(H)
    D = np.eye(2)
    D[1, 1] = np.sign(np.linalg.det(Vt.T @ U.T))
    R_2d = Vt.T @ D @ U.T

    yaw_angle = np.arctan2(R_2d[1, 0], R_2d[0, 0])
    R = _rot_about(Z, yaw_angle) @ R_align

    ml = np.asarray(local_pts, float).mean(0)
    mw = np.asarray(world_pts, float).mean(0)
    t_unconstrained = mw - R @ ml
    
    t_z = np.dot(wo - R @ lo, wn)
    t = t_unconstrained - np.dot(t_unconstrained, wn) * wn + t_z * wn

    return {"R": R.tolist(), "t_mm": t.tolist()}


# ---- ENFORCE: seat a part COAXIAL to an axle (revolute/slider) ---------------
# A fasten pattern over-determines all 6 DOF (Kabsch above). A revolute/slider
# does NOT: the joint pins a part onto an AXIS and leaves one DOF free -- spin
# about the axis (revolute) or slide along it (slider). So there is no point set
# to Kabsch; we align the part's local axis onto the target axle's world axis and
# pick the free DOF by convention (spin_rad / along_mm, default 0). This is the
# honest pose for a pulley on an axle: 4 DOF solved by the axis, 1 left free.

def _rot_about(axis, ang) -> np.ndarray:
    """Rotation by `ang` rad about a unit-ish `axis` (Rodrigues)."""
    k = _unit(np.asarray(axis, float))
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * (K @ K)


def _rot_align(d_from, d_to) -> np.ndarray:
    """Minimal rotation taking unit d_from onto unit d_to."""
    a, b = _unit(np.asarray(d_from, float)), _unit(np.asarray(d_to, float))
    v = np.cross(a, b)
    s = float(np.linalg.norm(v))
    c = float(np.dot(a, b))
    if s < 1e-12:                                   # already (anti)parallel
        if c > 0:
            return np.eye(3)
        perp = np.cross(a, [1, 0, 0])               # antiparallel: flip 180 deg
        if np.linalg.norm(perp) < 1e-9:
            perp = np.cross(a, [0, 1, 0])
        return _rot_about(perp, np.pi)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx * ((1 - c) / (s * s))


def solve_coaxial(local_axis: dict, world_axis: dict,
                  spin_rad: float = 0.0, along_mm: float = 0.0) -> dict:
    """Pose seating a part COAXIAL to a target axle. Aligns the part's local axis
    onto the world axis; the on-axis DOF is FREE and chosen here: `spin_rad` is the
    free DOF of a revolute (rotation about the axis), `along_mm` the free DOF of a
    slider (translation along it). Default 0/0 places the local axis origin on the
    world axis origin with no extra spin -- a canonical seat the caller can offset."""
    dl, dw = _unit(np.asarray(local_axis["d"], float)), _unit(np.asarray(world_axis["d"], float))
    R = _rot_about(dw, spin_rad) @ _rot_align(dl, dw)
    o_target = np.asarray(world_axis["o"], float) + along_mm * dw
    t = o_target - R @ np.asarray(local_axis["o"], float)
    return {"R": R.tolist(), "t_mm": t.tolist()}


@dataclass
class MateReport:
    part: str
    pose: dict
    enforce_rms_mm: float
    checks: list = field(default_factory=list)        # list[Residual]
    mode: str = "fasten pattern"                       # how the pose was solved

    @property
    def ok(self) -> bool:
        return all(c.satisfied() for c in self.checks)

    def text(self) -> str:
        lines = [f"[{self.part}] pose SOLVED from {self.mode} "
                 f"(enforce residual {self.enforce_rms_mm:.3f} mm):"]
        for c in self.checks:
            verdict = "REDUNDANT-OK" if c.satisfied() else "VIOLATED"
            lines.append(f"   check {c.ctype}({c.a} = {c.b}): {c.detail}  -> {verdict}")
        return "\n".join(lines)


def _local_geo(library, addr):
    ref, fid = addr.split(".", 1)
    return library[ref].feat(fid)


def _eval_checks(check_constraints, library, placements) -> list:
    """Evaluate each (ctype, a_addr, b_addr) as a world residual at solved poses."""
    checks = []
    for ctype, a_addr, b_addr in check_constraints:
        ra = a_addr.split(".", 1)[0]
        rb = b_addr.split(".", 1)[0]
        A = world_geom(_local_geo(library, a_addr), placements[ra])
        B = world_geom(_local_geo(library, b_addr), placements[rb])
        checks.append(residual(ctype, A, B, a_addr, b_addr))
    return checks


def enforce_and_check(part_ref: str, hole_pairs, check_constraints, library,
                      placements) -> MateReport:
    """hole_pairs: list of (local_hole_geo, world_hole_addr) -- the fasten pattern
    that ENFORCES the pose. check_constraints: list of (ctype, local_feat_addr,
    other_feat_addr) evaluated AFTER the pose is solved.
    `library[ref].feat(fid)` -> local feature geometry dict; `placements` gives
    other parts' poses (already solved)."""
    local_pts, world_pts = [], []
    for local_geo, world_addr in hole_pairs:
        ref, fid = world_addr.split(".", 1)
        wf = world_geom(library[ref].feat(fid), placements[ref])
        local_pts.append(local_geo["o"] if local_geo["kind"] != "point" else local_geo["p"])
        world_pts.append(wf["o"] if wf["kind"] != "point" else wf["p"])
    pose = solve_rigid(local_pts, world_pts)
    placements[part_ref] = pose

    # enforce residual (how well the solved pose hits the holes)
    err = []
    for lp, wp in zip(local_pts, world_pts):
        err.append(np.linalg.norm(xf_point(pose, lp) - np.asarray(wp)))
    rms = float(np.sqrt(np.mean(np.square(err))))

    checks = _eval_checks(check_constraints, library, placements)
    return MateReport(part_ref, pose, rms, checks)


def enforce_coaxial_and_check(part_ref: str, local_axis_addr: str,
                              world_axis_addr: str, check_constraints, library,
                              placements, joint: str = "revolute",
                              spin_rad: float = 0.0, along_mm: float = 0.0) -> MateReport:
    """ENFORCE a revolute/slider: seat `part_ref` coaxial to the axle named by
    `world_axis_addr` (an already-placed part's axis feature), aligning the part's
    own `local_axis_addr` feature onto it. The on-axis DOF stays free (revolute ->
    spin_rad, slider -> along_mm). Then evaluate `check_constraints` as residuals,
    exactly like the fasten path. The enforce residual is the axis-vs-axis offset
    (~0 by construction): the joint pins the axis, nothing over-determines it."""
    if joint not in ("revolute", "slider"):
        raise ValueError(f"enforce_coaxial_and_check: joint must be revolute/slider, got {joint!r}")
    la = _local_geo(library, local_axis_addr)
    wa = world_geom(_local_geo(library, world_axis_addr),
                    placements[world_axis_addr.split(".", 1)[0]])
    pose = solve_coaxial(la, wa, spin_rad=spin_rad, along_mm=along_mm)
    placements[part_ref] = pose

    # enforce residual: the solved part axis should lie ON the world axle axis.
    pa = world_geom(la, pose)
    r = residual("coaxial", pa, wa)
    rms = float(np.hypot(r.pos_mm, r.ang_rad * 1000.0))   # mm + (rad->"mm" at 1 m arm)

    checks = _eval_checks(check_constraints, library, placements)
    return MateReport(part_ref, pose, rms, checks, mode=f"{joint} axle (coaxial)")
