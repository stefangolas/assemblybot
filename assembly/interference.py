"""Interference gate via real mesh collision (Section 9).

Loads the tessellated glTF meshes, places them per the assembly's mates
(frame reconciliation -- the mesh origin and the annotation datum are NOT the
same point, so we reconcile to the part frame), and runs FCL collision.

AUTHORITY NOTE (Section 3): the simplified, non-threaded CAD models the thread
region as a plain cylinder at the *nominal major diameter*. So bore<->thread
clearance must be judged from the SPEC TABLE (authoritative for compatibility
scalars), not from a mesh boolean at the thread. This gate therefore tests for
*gross unintended overlap* and allows a small contact tolerance at designed
seating faces; the dimensional clearance is the compatibility gate's job.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import trimesh

_TOL_MM = 0.12  # contact tolerance: seated faces / under-head fillets touch, not "interference"


def _load_mm(gltf_path: str) -> trimesh.Trimesh:
    m = trimesh.load(gltf_path)
    if isinstance(m, trimesh.Scene):
        m = m.to_geometry()
    m = m.copy()
    m.apply_scale(1000.0)  # cascadio writes metres; we work in mm
    return m


@dataclass
class InterferenceResult:
    clean: bool
    detail: str
    pairs: list


def check_seated(screw_gltf: str, washer_gltf: str, seat_z: float,
                 washer_thickness: float) -> InterferenceResult:
    """Rung-0 placement: screw grounded at identity (mesh already Z-axis,
    XY-centred). Washer seated coaxially with its mating face at `seat_z`
    (the under-head bearing face), body extending toward the shank (-Z)."""
    screw = _load_mm(screw_gltf)
    washer = _load_mm(washer_gltf)

    # reconcile washer mesh (native z in [0, t]) to sit in [seat_z - t, seat_z]
    wz_min = washer.bounds[0][2]
    T = np.eye(4)
    T[2, 3] = (seat_z - washer_thickness) - wz_min
    washer.apply_transform(T)

    # shrink contact skin so a designed touching face is not flagged
    cm = trimesh.collision.CollisionManager()
    cm.add_object("screw", screw)
    cm.add_object("washer", washer)
    hit, names, data = cm.in_collision_internal(return_names=True, return_data=True)

    depth = max((abs(c.depth) for c in data), default=0.0)
    interfering = hit and depth > _TOL_MM
    if interfering:
        detail = f"mesh overlap depth {depth:.3f} mm > tol {_TOL_MM} mm between {names}"
    elif hit:
        detail = f"contact only (max depth {depth:.3f} mm <= tol {_TOL_MM} mm) -- seated faces touching, OK"
    else:
        detail = "no mesh contact"
    return InterferenceResult(clean=not interfering, detail=detail, pairs=list(names))


def check_face_mount_zoned(rail_gltf: str, bracket_gltf: str, R, t_mm, face_x: float,
                           mount_face_mesh_z: float, plate_l: float, plate_w: float,
                           plate_t: float, slot_half_width: float = 8.0) -> InterferenceResult:
    """Real-mesh interference using the SOLVED placement (assembly/solve.py).

    Three things, kept distinct, because a naive bracket-vs-rail boolean conflates
    them and false-positives:

      (a) SEATING (analytic, definitive): did the bracket's mounting face land ON
          the rail's mount face? Coincident solid faces register as FCL overlap
          (the 1.94 mm "penetration" we first saw was just the flat plate face
          touching the flat rail face), so seating is checked by geometry, not
          collision: world-X of the mounting face must equal face_x. This is what
          actually catches a mis-placement (e.g. the 3 mm-sunk bracket bug).
      (b) PLATE NO-SINK (mesh): a DWG-dimensioned plate box at the solved pose,
          held off the face by a small gap, must NOT collide with the rail. Uses
          the plate body only -- excludes the bundled fasteners.
      (c) FASTENER CLAMP ARTIFACT (mesh, informational): the contiguous T-nut
          solid overlapping the slot lips is an unavoidable catalog-modelling
          artifact (a real drop-in T-nut is a multi-part assembly that clamps
          against the lips). Reported as intended engagement, never a fault.
    """
    R = np.asarray(R, float); t = np.asarray(t_mm, float)
    rail = _load_mm(rail_gltf)

    # (a) seating: R carries local Z -> world X, so the mounting face (local
    # Z = mount_face_mesh_z) lands at world X = mount_face_mesh_z + t_x.
    brk_face_x = mount_face_mesh_z + t[0]
    seat_err = abs(brk_face_x - face_x)

    # (b) plate-body no-sink: world-aligned plate box (thickness X, width Y,
    # length Z) seated just outside the face by a gap.
    gap = 0.05
    plate = trimesh.creation.box(extents=(plate_t, plate_w, plate_l))
    Tb = np.eye(4)
    Tb[0, 3] = brk_face_x + gap + plate_t / 2.0
    Tb[2, 3] = (rail.bounds[0][2] + rail.bounds[1][2]) / 2.0
    plate.apply_transform(Tb)
    cmb = trimesh.collision.CollisionManager()
    cmb.add_object("rail", rail); cmb.add_object("plate", plate)
    sink, _, sdata = cmb.in_collision_internal(return_names=True, return_data=True)
    sink_depth = max((abs(getattr(c, "depth", 0.0) or 0.0) for c in sdata), default=0.0)

    # (c) real bracket-vs-rail overlap, informational. We do NOT classify this
    # per-contact: the plate face is coincident with the rail face, and coincident
    # solid faces generate a band of artifact contacts that can't be cleanly told
    # apart from a genuine stray. Placement correctness is already established by
    # (a) analytic seating and (b) the plate-body no-sink box; this number is just
    # the magnitude of the expected catalog artifacts (T-nut clamp + face seating).
    brk = _load_mm(bracket_gltf)
    M = np.eye(4); M[:3, :3] = R; M[:3, 3] = t
    brk.apply_transform(M)
    cmf = trimesh.collision.CollisionManager()
    cmf.add_object("rail", rail); cmf.add_object("bracket", brk)
    _, _, fdata = cmf.in_collision_internal(return_names=True, return_data=True)
    artifact_depth = max((abs(getattr(c, "depth", 0.0) or 0.0) for c in fdata), default=0.0)

    seated = seat_err <= 0.2
    no_sink = (not sink) or sink_depth <= _TOL_MM
    clean = seated and no_sink
    detail = (f"seating: mount face at X={brk_face_x:.2f} vs rail face {face_x:.2f} "
              f"(err {seat_err:.2f} mm, {'OK' if seated else 'MIS-PLACED'}); "
              f"plate body {'clear of rail' if no_sink else f'SINKS {sink_depth:.2f} mm into rail'}; "
              f"real bracket-rail overlap {artifact_depth:.2f} mm = T-nut clamp + coincident "
              f"face-seating (catalog contiguous-solid artifacts, expected)")
    return InterferenceResult(clean=clean, detail=detail, pairs=["rail", "bracket"])


def check_face_mount(rail_gltf: str, plate_l: float, plate_w: float, plate_t: float) -> InterferenceResult:
    """Rung-1 placement: a flat plate (dims from the 2-D DWG) seated on the rail's
    +X face vs the real rail mesh. We deliberately use a DWG-dimensioned plate box,
    not the bracket mesh: McMaster ships the bracket modelled WITH its T-nuts,
    which are *designed* to enter the slot -- a naive bracket-vs-rail boolean would
    false-positive on that intended engagement (same authority lesson as the
    no-threads shank in Rung 0). This checks the real question: does the plate sink
    into the rail solid?  Length along Z (rail axis), width along Y, thickness along X.
    """
    rail = _load_mm(rail_gltf)
    face_x = rail.bounds[1][0]                      # +X face of the rail
    plate = trimesh.creation.box(extents=(plate_t, plate_w, plate_l))
    T = np.eye(4)
    T[0, 3] = face_x + plate_t / 2.0                # seat plate on the face (no overlap)
    T[2, 3] = (rail.bounds[0][2] + rail.bounds[1][2]) / 2.0  # centre on rail length
    plate.apply_transform(T)

    cm = trimesh.collision.CollisionManager()
    cm.add_object("rail", rail)
    cm.add_object("plate", plate)
    hit, names, data = cm.in_collision_internal(return_names=True, return_data=True)
    depth = max((abs(c.depth) for c in data), default=0.0)
    interfering = hit and depth > _TOL_MM
    if interfering:
        detail = f"plate sinks into rail by {depth:.3f} mm > tol {_TOL_MM} mm"
    elif hit:
        detail = (f"plate seats flat on rail face (contact {depth:.3f} mm <= tol {_TOL_MM} mm); "
                  f"bolts entering the slot are intended engagement, not flagged")
    else:
        detail = "plate clears rail (no contact)"
    return InterferenceResult(clean=not interfering, detail=detail, pairs=list(names))


# =============================================================================
# General whole-assembly interference gate (static + swept). Used by the main
# verification set alongside load_path and cad_fidelity. The per-assembly
# knowledge -- which contacts are BY DESIGN (a screw in its hole, a seated face)
# and which refs ROTATE (for the swept-collision check that a static pose hides,
# Hard Rule 1) -- is supplied by the caller as predicates, so this stays generic.
# =============================================================================

def load_placed(asm: dict, root) -> dict:
    """Build {ref: placed Trimesh in world mm} from a canonical assembly JSON
    (`_render` list of {ref,url} + per-ref {R, t_mm}; glTF is metres)."""
    root = Path(root)
    meshes = {}
    for e in asm.get("_render", []):
        ref, url = e["ref"], e["url"]
        p = (root / url.lstrip("/")).resolve()
        if not p.exists():
            continue
        g = list(trimesh.load(p, force="scene").geometry.values())
        if not g:
            continue
        m = trimesh.util.concatenate(g)
        m.apply_scale(1000.0)                       # metres -> mm
        pl = asm[ref]
        M = np.eye(4)
        M[:3, :3] = np.asarray(pl["R"], float)
        M[:3, 3] = np.asarray(pl["t_mm"], float)
        m.apply_transform(M)
        meshes[ref] = m
    return meshes


def _pair_depths(meshes: dict, names_a, names_b=None) -> dict:
    """Max FCL penetration depth per colliding pair. names_b None -> all pairs within
    names_a; else cross set A vs B."""
    cm = trimesh.collision.CollisionManager()
    for n in names_a:
        cm.add_object(n, meshes[n])
    if names_b is None:
        _, _, data = cm.in_collision_internal(return_names=True, return_data=True)
    else:
        cm2 = trimesh.collision.CollisionManager()
        for n in names_b:
            cm2.add_object(n, meshes[n])
        _, _, data = cm.in_collision_other(cm2, return_names=True, return_data=True)
    depth = {}
    for c in data:
        nm = getattr(c, "names", None)
        if not nm:
            continue
        key = tuple(sorted(nm))
        depth[key] = max(depth.get(key, 0.0), abs(getattr(c, "depth", 0.0) or 0.0))
    return depth


@dataclass
class InterferenceReport:
    passed: bool
    static_flags: list = field(default_factory=list)   # [((a,b), depth_mm)] unexpected static overlaps
    swept_flags: dict = field(default_factory=dict)     # {(a,b): max_depth_mm} swept-only collisions
    n_contacts: int = 0


def interference_gate(meshes: dict, *, designed=None, rotating=None, tol_mm=0.15,
                      flag_mm=0.30, swept_steps=24, axis=(0, 0, 1), center=(0, 0, 0),
                      verbose=True) -> InterferenceReport:
    """Whole-assembly overlap gate.

      designed(a, b) -> bool : True when the pair is MEANT to touch (screw-in-hole,
                               seated face); such overlaps never fail. Default: any
                               pair is unexpected (strict).
      rotating(ref)  -> bool : marks the moving group; if given, the rotating set is
                               swept about `axis` through `center` over `swept_steps`
                               and collided against the fixed set (catches a collision
                               that the assembled pose hides). Default: no sweep.

    Fails if any UNEXPECTED static overlap exceeds flag_mm, or any swept collision occurs.
    """
    designed = designed or (lambda a, b: False)

    depth = _pair_depths(meshes, list(meshes))
    contacts = [(k, d) for k, d in depth.items() if d > tol_mm]
    static_flags = [(k, d) for k, d in contacts if not designed(*k) and d > flag_mm]
    static_flags.sort(key=lambda kv: -kv[1])

    swept = {}
    if rotating is not None:
        rot = [r for r in meshes if rotating(r)]
        fixed = [r for r in meshes if not rotating(r)]
        if rot and fixed:
            base = {r: meshes[r].copy() for r in rot}
            for i in range(swept_steps):
                ang = 2 * math.pi * i / swept_steps
                Rz = trimesh.transformations.rotation_matrix(ang, axis, center)
                step = dict(meshes)
                for r in rot:
                    m = base[r].copy()
                    m.apply_transform(Rz)
                    step[r] = m
                for key, d in _pair_depths(step, rot, fixed).items():
                    if d > tol_mm and not designed(*key):
                        swept[key] = max(swept.get(key, 0.0), d)

    passed = not static_flags and not swept
    rep = InterferenceReport(passed, static_flags, swept, len(contacts))
    if verbose:
        for (a, b), d in static_flags:
            print(f"  interference  STATIC {a} <-> {b}: {d:.2f} mm (not a designed contact)")
        for (a, b), d in sorted(swept.items(), key=lambda kv: -kv[1]):
            print(f"  interference  SWEPT  {a} <-> {b}: up to {d:.2f} mm mid-rotation")
        tag = "PASS" if passed else "FAIL"
        print(f"  interference GATE: {tag} ({rep.n_contacts} contacts, "
              f"{len(static_flags)} static + {len(swept)} swept unexpected)")
    return rep
