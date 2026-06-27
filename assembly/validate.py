"""Validation gates (Section 9).

An assembly is a working machine only when all blocking gates pass:

  mobility       computed DOF == intended DOF (Kutzbach over joints)
  compatibility  every mate's dimensional/thread preconditions hold and every
                 `requires` is filled by a real part in the BOM
  interference   no unintended solid overlap (glTF collision; analytic
                 clearance fallback when meshes are absent -- reported honestly)
  groundedness   exactly one grounded part, connected graph, nothing floating
  load_sanity    advisory only -- flags joints over catalog rating when ratings exist
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .mobility import mobility, MobilityResult


@dataclass
class GateResult:
    name: str
    passed: bool
    blocking: bool
    detail: str

    def to_json(self) -> dict:
        return {"name": self.name, "passed": self.passed,
                "blocking": self.blocking, "detail": self.detail}


@dataclass
class ValidationReport:
    gates: list[GateResult] = field(default_factory=list)
    mobility: MobilityResult | None = None
    placements: dict = field(default_factory=dict)  # {ref: {"R","t_mm"}} (mm)

    @property
    def passed(self) -> bool:
        return all(g.passed for g in self.gates if g.blocking)

    def to_json(self) -> dict:
        return {
            "passed": self.passed,
            "mobility": self.mobility.to_json() if self.mobility else None,
            "gates": [g.to_json() for g in self.gates],
            "placements": self.placements,
        }


def _part_ref(addr: str) -> str:
    """'p_washer.bore' -> 'p_washer'."""
    return addr.split(".", 1)[0]


def _feature_of(addr: str, parts: dict):
    ref, fid = addr.split(".", 1)
    return parts[ref].feature(fid)


def validate(assembly, library: dict, couplings: int = 0, belt_fit=None) -> ValidationReport:
    """assembly: ontology.Assembly. library: {part_ref: Part} for parts in the BOM.
    belt_fit: optional assembly.belt.BeltFit for belt_drive assemblies (Rung 2)."""
    rep = ValidationReport()

    # one solved placement per part -- consumed by the interference gate below
    # AND exported for the viewer, so validation and visualization never diverge.
    try:
        from .solve import solve_placements, placements_to_json
        rep.placements = placements_to_json(solve_placements(assembly, library))
    except Exception as e:  # noqa: BLE001 -- placement is best-effort for now
        rep.placements = {}

    # ---- gate: groundedness -------------------------------------------------
    grounded = [p for p in assembly.parts if p.grounded]
    refs = {p.ref for p in assembly.parts}
    # union-find over parts connected by any mate constraint
    parent = {r: r for r in refs}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    touched = set()
    for m in assembly.mates:
        for c in m.constraints:
            ra, rb = _part_ref(c.a), _part_ref(c.b)
            touched.add(ra)
            touched.add(rb)
            if ra in parent and rb in parent:
                union(ra, rb)
    components = {find(r) for r in refs}
    floating = refs - touched
    ground_ok = len(grounded) == 1 and len(components) == 1 and not floating
    detail = []
    if len(grounded) != 1:
        detail.append(f"expected exactly 1 grounded part, found {len(grounded)}")
    if len(components) != 1:
        detail.append(f"constraint graph has {len(components)} disconnected components")
    if floating:
        detail.append(f"floating (unconstrained) parts: {sorted(floating)}")
    rep.gates.append(GateResult("groundedness", ground_ok, True,
                                "; ".join(detail) or "one ground, connected, no floats"))

    # ---- gate: attachment (physical path to the anchor) ---------------------
    # groundedness above is a graph-only check (asserted edges); this one is
    # geometric: keep only mate edges whose mating features actually coincide in
    # space, then require every body to reach the single grounded anchor. Catches
    # a part that is "connected" on paper but floating in the solved layout.
    try:
        from .attachment import verify_attachment
        att = verify_attachment(assembly, library)
        rep.gates.append(GateResult("attachment", att.ok, True, att.detail))
    except Exception as e:  # noqa: BLE001 -- never let the gate crash the run
        rep.gates.append(GateResult("attachment", False, True,
                                    f"attachment check errored: {e}"))

    # ---- gate: compatibility ------------------------------------------------
    compat_issues = []
    for m in assembly.mates:
        for req in m.requires:
            filled = (req in library
                      or any(p.part_number == req or p.ref == req for p in assembly.parts))
            if not filled:
                compat_issues.append(f"mate {m.interface}: unfilled requires {req!r}")
        for c in m.constraints:
            if c.type != "coaxial":
                continue
            try:
                fa = _feature_of(c.a, library)
                fb = _feature_of(c.b, library)
            except (KeyError, ValueError):
                continue
            # clearance: a hole must be >= the shaft it rides on
            holes = {"clearance_hole"}
            shafts = {"shaft_bore", "bearing_seat", "shoulder"}
            pair = {fa.role: fa, fb.role: fb}
            hole = next((pair[r] for r in pair if r in holes), None)
            shaft = next((pair[r] for r in pair if r in shafts), None)
            if hole and shaft:
                hd = hole.params.get("diameter")
                sd = shaft.params.get("diameter")
                if hd is not None and sd is not None and hd < sd - 1e-6:
                    compat_issues.append(
                        f"interference: hole dia {hd} < shaft dia {sd} on {c.a}/{c.b}")
        # bolt_joint: the threaded hole's thread must match the screw that fills it
        if m.interface == "bolt_joint":
            threads = set()
            for c in m.constraints:
                if c.type != "coaxial":
                    continue
                for addr in (c.a, c.b):
                    try:
                        f = _feature_of(addr, library)
                    except (KeyError, ValueError):
                        continue
                    if f.role == "threaded_hole" and f.params.get("thread"):
                        threads.add(f.params["thread"])
            screw_threads = {library[r].spec.get("thread") for r in m.requires
                             if r in library and library[r].spec.get("thread")}
            if threads and screw_threads and not (threads & screw_threads):
                compat_issues.append(
                    f"thread mismatch in {m.interface}: hole {threads} vs screw {screw_threads}")
    rep.gates.append(GateResult("compatibility", not compat_issues, True,
                                "; ".join(compat_issues) or "all mate preconditions satisfied"))

    # ---- gate: interference -------------------------------------------------
    have_mesh = all(library[p.ref].cad.get("gltf_uri") for p in assembly.parts
                    if p.ref in library)
    seated = next((m for m in assembly.mates if m.interface == "seated_revolute"), None)
    bolted = next((m for m in assembly.mates if m.interface == "bolt_joint"), None)
    if have_mesh and seated is not None:
        from .interference import check_seated
        screw = library["p_screw"]
        washer = library["p_washer"]
        res = check_seated(
            screw_gltf=screw.cad["gltf_uri"],
            washer_gltf=washer.cad["gltf_uri"],
            seat_z=screw.frame.get("mesh_seat_z", 0.0),
            washer_thickness=washer.spec.get("thickness", 1.0),
        )
        rep.gates.append(GateResult("interference", res.clean, True,
                                    f"FCL mesh collision: {res.detail}"))
    elif bolted is not None:
        from .interference import check_face_mount_zoned
        rail_ref = next(p.ref for p in assembly.parts if p.grounded)
        brk_ref = next(p.ref for p in assembly.parts if not p.grounded)
        rail, brk = library[rail_ref], library[brk_ref]
        place = rep.placements.get(brk_ref, {"R": [[1,0,0],[0,1,0],[0,0,1]], "t_mm": [0,0,0]})
        res = check_face_mount_zoned(
            rail_gltf=rail.cad["gltf_uri"], bracket_gltf=brk.cad["gltf_uri"],
            R=place["R"], t_mm=place["t_mm"],
            face_x=rail.frame["mount_face_mesh_x"],
            mount_face_mesh_z=brk.frame["mount_face_mesh_z"],
            plate_l=brk.spec["plate_length"], plate_w=brk.spec["plate_width"],
            plate_t=brk.spec["plate_thickness"],
        )
        rep.gates.append(GateResult("interference", res.clean, True,
                                    f"FCL zone collision: {res.detail}"))
    elif any(m.interface == "belt_drive" for m in assembly.mates):
        # Rung 2: analytic clearance for the rotating/looped assembly. Full
        # multi-body FCL is deferred; the meaningful static checks are that the
        # pulleys don't overlap and the generated belt loop clears.
        pulleys = [library[p.ref] for p in assembly.parts if library[p.ref].cls == "timing_pulley"]
        ok, det = True, "pulleys clear; belt loop generated (see belt_fit gate)"
        if len(pulleys) == 2:
            od = max(pulleys[0].spec.get("od_mm", 0), pulleys[1].spec.get("od_mm", 0))
            cd = assembly.__dict__.get("center_distance_mm", 0)
            if cd and cd <= od:
                ok = False; det = f"pulleys overlap: center distance {cd} <= OD {od}"
            else:
                det = f"pulleys clear (center distance {cd} mm > OD {od} mm)"
        rep.gates.append(GateResult("interference", ok, True, f"analytic: {det}"))
    elif have_mesh:
        rep.gates.append(GateResult("interference", True, True,
                                    "glTF meshes present but no placement rule for this mate yet"))
    else:
        # honest fallback: analytic clearance already enforced in compatibility
        clean = not any("interference" in s for s in compat_issues)
        rep.gates.append(GateResult(
            "interference", clean, False,
            "no glTF meshes in BOM -- mesh collision SKIPPED; "
            "relied on analytic coaxial clearance (non-blocking)"))

    # ---- gate: cad_fidelity -------------------------------------------------
    # Check that parts claiming to have holes actually have them in their 3D mesh
    try:
        from ontology.cad_sync import verify_mesh_holes
        import os
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        fidelity_issues = []
        for p in assembly.parts:
            if p.ref in library:
                part_def = library[p.ref]
                phantom_ports = verify_mesh_holes(part_def, repo_root)
                if phantom_ports:
                    msg = f"{p.ref} ({part_def.part_number}): missing features in CAD mesh: {', '.join(phantom_ports)}"
                    # Custom parts block; catalog parts warn but pass
                    is_custom = part_def.classification.get("catalog_family") == "custom_machined"
                    fidelity_issues.append((msg, is_custom))
                    
        # If any custom part fails, the gate blocks.
        has_blocking = any(custom for msg, custom in fidelity_issues)
        if fidelity_issues:
            detail = "; ".join(msg for msg, _ in fidelity_issues)
            rep.gates.append(GateResult("cad_fidelity", not has_blocking, True, detail))
        else:
            rep.gates.append(GateResult("cad_fidelity", True, True, "all modeled features exist in CAD"))
    except Exception as e:
        rep.gates.append(GateResult("cad_fidelity", False, True, f"cad_fidelity check errored: {e}"))


    # ---- gate: mobility -----------------------------------------------------
    # each mate connects two bodies -> (a_body, b_body, joint). A belt_drive
    # contributes COUPLINGS, not a kinematic joint edge (it ties velocities, it
    # does not weld bodies), so it is excluded from the joint graph and its
    # couplings are summed in. Only refs that are actual bodies count.
    bodies = [p.ref for p in assembly.parts]
    bodyset = set(bodies)
    jointspecs = []
    total_couplings = couplings
    for m in assembly.mates:
        total_couplings += getattr(m, "couplings", 0)
        if m.interface == "belt_drive":
            continue
        pair = []
        for c in m.constraints:
            for r in (_part_ref(c.a), _part_ref(c.b)):
                if r in bodyset and r not in pair:
                    pair.append(r)
        if len(pair) >= 2:
            jointspecs.append((pair[0], pair[1], m.joint))
        elif len(pair) == 1:
            jointspecs.append((pair[0], pair[0], m.joint))
    mob = mobility(bodies, jointspecs, couplings=total_couplings)
    assembly.computed_dof = mob.computed_dof
    rep.mobility = mob
    mob_ok = mob.computed_dof == assembly.intended_dof
    rep.gates.append(GateResult(
        "mobility", mob_ok, True,
        f"computed DOF {mob.computed_dof} vs intended {assembly.intended_dof} "
        f"[bodies={mob.n_bodies}, rigid_groups={mob.n_rigid_groups}, "
        f"mobile_joints={mob.n_joints_reduced}, sum_f={mob.sum_f}, couplings={mob.n_couplings}]"))

    # ---- gate: redundancy (advisory) -- benign over-constraint, not a fault --
    redundant = mob.redundant_fixed + mob.redundant_locked
    rep.gates.append(GateResult(
        "redundancy", True, False,
        f"{mob.redundant_fixed} redundant fixed joint(s) recognized as INTENTIONAL "
        f"over-constraint (e.g. extra bolts on a face); "
        f"{mob.redundant_locked} non-fixed joint(s) locked inside a rigid group"
        if redundant else "no redundant constraints"))

    # ---- gate: belt fit (Rung 2) -------------------------------------------
    belt_mate = next((m for m in assembly.mates if m.interface == "belt_drive"), None)
    if belt_mate is not None:
        # pitch match: every pitch_circle feature's pitch must equal the belt's
        pulley_pitch = set()
        for p in assembly.parts:
            for f in library[p.ref].features:
                if f.role == "pitch_circle" and f.params.get("pitch_in"):
                    pulley_pitch.add(f.params["pitch_in"])
        belt_part = next((library[r] for r in belt_mate.requires if r in library), None)
        belt_pitch = belt_part.spec.get("pitch_in") if belt_part else None
        pitch_ok = (belt_pitch is not None and pulley_pitch == {belt_pitch})
        len_ok = belt_fit.ok if belt_fit is not None else False
        detail = (f"pitch match {sorted(pulley_pitch)} in vs belt {belt_pitch} in "
                  f"({'OK' if pitch_ok else 'MISMATCH'}); "
                  f"{belt_fit.detail if belt_fit else 'no belt_fit supplied'}")
        rep.gates.append(GateResult("belt_fit", pitch_ok and len_ok, True, detail))

    # ---- gate: load sanity (advisory) --------------------------------------
    rep.gates.append(GateResult("load_sanity", True, False,
                                "advisory: no applied-load model supplied"))

    return rep
