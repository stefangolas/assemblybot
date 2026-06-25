"""Pose solving FROM template `enforce` relations (migration step A.8 bridge).

This is the load-bearing seam the r7 STATE flagged as "next, FIRST": the demos so
far PLACED each pair by hand to exercise the CHECKS, but the template's `enforce`
relations (`coaxial`, `oppose_and_seat`) never actually DROVE a pose. This module
closes that: given an `AttachmentInstance`, the ref of the body to SOLVE, the v2
library, and the placements of the already-located bodies, it reads the template's
`enforce` relations, pulls the relevant port/group geometry, and calls the
`assembly.mate_solver` primitives to PRODUCE the moving body's `{R, t_mm}` pose.

Strict, never-fudge (Hard Rule 5): it solves ONLY from the parts' MEASURED ports.
There is no hand-picked target coordinate; the moving body's own port axis / hole
group is aligned to the fixed body's measured port axis / hole group. An enforce
relation it cannot honestly solve raises `NotImplementedError` rather than placing
the part somewhere plausible-looking.

Two enforce forms are supported -- exactly what the rung-2 moving group needs:

  * `coaxial(A.axis, B.axis)`  -> revolute/slider seat (`mate_solver.solve_coaxial`).
       The on-axis DOF stays FREE (spin_rad for a revolute, along_mm for a slider).
  * `oppose_and_seat(A.face, B.face)` WITH a bolt-pattern group bound on each side
       -> rigid fasten (`mate_solver.solve_rigid`), with the 1-1 hole correspondence
       SEARCHED over permutations (never zipped by accident; Section 4) and the
       lowest-RMS Kabsch fit kept.

After solving, `placements[solve_ref]` is written and the same `AttachmentInstance`
can be `.evaluate()`d -- the look and the engine then check the very pose we solved.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import permutations

import numpy as np

from assembly import mate_solver as MS
from . import ports_match as PM


# ---- resolving an enforce-relation endpoint to local geometry -----------------

@dataclass
class _Endpoint:
    ref: str
    part: object          # PartDefinition
    port: object          # EngagementPort
    place: dict | None
    elem: str             # 'axis' | 'face' | 'sweep' | 'support'


def _resolve_endpoint(instance, addr: str, library, placements) -> _Endpoint:
    """`addr` is a template relation address `slot.elem` (e.g. 'rotor.axis'). The
    slot is bound (instance.bindings) to a real `part.port`; `elem` names which
    geometric element of that port the relation acts on."""
    slot, _, elem = addr.partition(".")
    bound = instance.bindings.get(slot)
    if bound is None or ":" in bound or "." not in bound:
        raise ValueError(f"pose_solve: enforce slot {slot!r} -> {bound!r} is not a "
                         f"real part.port address")
    ref, pid = bound.split(".", 1)
    part = library[ref]
    return _Endpoint(ref, part, part.port(pid), placements.get(ref), elem)


def _axis_feature(port) -> dict:
    """A cylindrical/threaded port's local axis as a mate_solver feature dict."""
    g = port.geometry
    if "axis" in g:
        a = g["axis"]
        return {"kind": "axis", "o": list(a["origin"]), "d": list(a["direction"])}
    if "sweep_path" in g and isinstance(g["sweep_path"], dict) and "origin" in g["sweep_path"]:
        a = g["sweep_path"]
        return {"kind": "axis", "o": list(a["origin"]), "d": list(a["direction"])}
    raise ValueError(f"port {port.id} ({port.family}) has no axis for a coaxial enforce")


# ---- pose solvers -------------------------------------------------------------

@dataclass
class PoseSolveResult:
    ref: str
    pose: dict
    mode: str
    enforce_rms_mm: float
    detail: str = ""
    extra: dict = field(default_factory=dict)

    def text(self) -> str:
        return (f"[{self.ref}] pose SOLVED from {self.mode} "
                f"(enforce residual {self.enforce_rms_mm:.4f} mm){'; ' + self.detail if self.detail else ''}")


def _solve_coaxial(instance, rel, solve_ref, library, placements,
                   spin_rad, along_mm, joint) -> PoseSolveResult:
    a = _resolve_endpoint(instance, rel.a, library, placements)
    b = _resolve_endpoint(instance, rel.b, library, placements)
    if a.ref == solve_ref:
        moving, fixed = a, b
    elif b.ref == solve_ref:
        moving, fixed = b, a
    else:
        raise ValueError(f"pose_solve: solve_ref {solve_ref!r} is in neither endpoint "
                         f"of coaxial({rel.a}, {rel.b})")
    if fixed.place is None:
        raise ValueError(f"pose_solve: the fixed body {fixed.ref!r} has no placement yet "
                         f"(solve its pose first)")
    local_axis = _axis_feature(moving.port)
    world_axis = MS.world_geom(_axis_feature(fixed.port), fixed.place)
    pose = MS.solve_coaxial(local_axis, world_axis, spin_rad=spin_rad, along_mm=along_mm)
    placements[solve_ref] = pose
    # enforce residual: the solved moving axis should lie ON the fixed world axis
    r = MS.residual("coaxial", MS.world_geom(local_axis, pose), world_axis)
    rms = float(np.hypot(r.pos_mm, r.ang_rad * 1000.0))
    return PoseSolveResult(solve_ref, pose, f"{joint} coaxial seat onto {fixed.ref}.{fixed.port.id}",
                           rms, r.detail)


def _group_for(instance, library, ref_filter, solve_ref, want_moving: bool):
    """Find the (def, group) bound via a ':'-group binding whose ref matches (or not)
    solve_ref. Returns (ref, part_def, PortGroup)."""
    for slot, addr in instance.bindings.items():
        if ":" not in addr:
            continue
        ref, gid = addr.split(":", 1)
        is_moving = (ref == solve_ref)
        if is_moving != want_moving:
            continue
        part = library[ref]
        grp = next(g for g in part.port_groups if g.id == gid)
        return ref, part, grp
    raise ValueError(f"pose_solve: no {'moving' if want_moving else 'fixed'} bolt-pattern "
                     f"group bound for {instance.template.id} (need a 'p:group' binding)")


def _local_origin(part_def, pid: str):
    """A port's positional anchor in its OWN frame (mm), mirroring ports_match."""
    g = part_def.port(pid).geometry
    if "axis" in g:
        return np.asarray(g["axis"]["origin"], float)
    if "plane" in g:
        return np.asarray(g["plane"]["origin"], float)
    if "support" in g and "axis" in g["support"]:
        return np.asarray(g["support"]["axis"]["origin"], float)
    raise ValueError(f"port {pid}: no positional anchor for pattern solve")


def _solve_pattern(instance, solve_ref, library, placements) -> PoseSolveResult:
    mref, mdef, mgrp = _group_for(instance, library, None, solve_ref, want_moving=True)
    fref, fdef, fgrp = _group_for(instance, library, None, solve_ref, want_moving=False)
    if placements.get(fref) is None:
        raise ValueError(f"pose_solve: fixed seat {fref!r} has no placement yet")
    if len(mgrp.members) != len(fgrp.members):
        raise ValueError(f"pose_solve: pattern sizes differ "
                         f"({len(mgrp.members)} vs {len(fgrp.members)})")
    n = len(mgrp.members)
    if n > 8:
        raise ValueError("pose_solve: pattern too large for brute correspondence (>8)")
    local_pts = [_local_origin(mdef, mb["port"]) for mb in mgrp.members]
    world_pts = [PM._port_world_origin(fdef, mb["port"], placements[fref]) for mb in fgrp.members]

    # Check if there is a hard seat plane constraint to combine with the pattern
    local_plane = None
    world_plane = None
    seat = [r for r in instance.template.enforce if r.type == "oppose_and_seat"]
    for r in seat:
        p_a = r.a.split(".", 1)[0]
        p_b = r.b.split(".", 1)[0]
        bind_a = instance.bindings.get(p_a, "")
        bind_b = instance.bindings.get(p_b, "")
        ref_a = bind_a.split(".")[0].split(":")[0] if bind_a else ""
        ref_b = bind_b.split(".")[0].split(":")[0] if bind_b else ""
        
        if ref_a == solve_ref or ref_b == solve_ref:
            def _get_plane(ref, bind, path):
                port_id = bind.split(".", 1)[1] if "." in bind else path.split(".", 1)[1]
                geo = library[ref].port(port_id).geometry
                raw_plane = geo["support"]["plane"] if path.endswith(".support") else geo["plane"]
                return {"kind": "plane", "o": raw_plane["origin"], "n": raw_plane["normal"]}
            
            if ref_a == solve_ref:
                local_plane = _get_plane(ref_a, bind_a, r.a)
                world_plane = MS.world_geom(_get_plane(ref_b, bind_b, r.b), placements[ref_b])
            else:
                local_plane = _get_plane(ref_b, bind_b, r.b)
                world_plane = MS.world_geom(_get_plane(ref_a, bind_a, r.a), placements[ref_a])
            break

    best = None  # (rms, pose, perm)
    for perm in permutations(range(n)):
        Wp = [world_pts[perm[i]] for i in range(n)]
        if local_plane and world_plane:
            pose = MS.solve_pattern_on_plane(local_pts, Wp, local_plane, world_plane)
        else:
            pose = MS.solve_rigid(local_pts, Wp)
        err = [np.linalg.norm(MS.xf_point(pose, local_pts[i]) - Wp[i]) for i in range(n)]
        rms = float(np.sqrt(np.mean(np.square(err))))
        if best is None or rms < best[0]:
            best = (rms, pose, perm)
    rms, pose, perm = best
    placements[solve_ref] = pose
    corr = [[mgrp.members[i]["port"], fgrp.members[perm[i]]["port"]] for i in range(n)]
    return PoseSolveResult(solve_ref, pose,
                           f"bolt-pattern fasten ({mref}:{mgrp.id} -> {fref}:{fgrp.id})",
                           rms, f"{n}-hole correspondence searched",
                           extra={"correspondence": corr})


# ---- public entry -------------------------------------------------------------

def solve_pose(instance, solve_ref, library, placements, *,
               spin_rad: float = 0.0, along_mm: float = 0.0) -> PoseSolveResult:
    """Solve `solve_ref`'s pose from `instance`'s template `enforce` relations and
    write it into `placements`. The fixed (reference) body must already be placed.

    `spin_rad`/`along_mm` set the FREE on-axis DOF for a coaxial revolute/slider seat.
    Raises NotImplementedError for an enforce form we will not solve honestly."""
    enf = instance.template.enforce
    joint = instance.template.result.type
    cox = [r for r in enf if r.type == "coaxial"]
    if cox:
        return _solve_coaxial(instance, cox[0], solve_ref, library, placements,
                              spin_rad, along_mm, joint)
    seat = [r for r in enf if r.type == "oppose_and_seat"]
    if seat:
        # honest pose needs the measured bolt pattern; require group bindings
        has_groups = any(":" in v for v in instance.bindings.values())
        if has_groups:
            return _solve_pattern(instance, solve_ref, library, placements)
        raise NotImplementedError(
            f"{instance.template.id}: oppose_and_seat without a bolt-pattern group "
            f"underdetermines the pose (a bare planar seat leaves 3 DOF). Bind the "
            f"measured hole groups, or use a coaxial/pattern template.")
    raise NotImplementedError(
        f"{instance.template.id}: no solvable enforce relation among "
        f"{[r.type for r in enf]} (belt route/mesh poses are generated, not solved here)")
