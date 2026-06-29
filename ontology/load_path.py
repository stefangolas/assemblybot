"""Load-path / closure gate -- three-state 'is this part really held?' (Section 5/6).

Closure rigor (user decision): a part is HELD only when there is a CONTINUOUS path
through real modeled parts and modeled engagement geometry to a grounded part, every
edge an instantiated attachment with checked geometry. 'Bore on an axis + a threaded
hole nearby => retention implied' is NOT a pass -- at best it is provisional.

Three states:
  HELD_CONFIRMED   complete modeled path; every edge's geometry PASSes and its
                   closure is a real fastener part or confirmed integral geometry.
  HELD_PROVISIONAL plausible, but some edge check is UNKNOWN or some closure is
                   asserted/inferred (e.g. integral closure declared but its
                   supporting port is only nominal).
  UNHELD           no path, or an edge geometry FAILs, or required closure is missing.

Final assembly validation requires HELD_CONFIRMED for every body; discovery/early
design may keep HELD_PROVISIONAL candidates.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import semantics as _SEM

CONFIRMED, PROVISIONAL, UNHELD = 2, 1, 0
# directive Section 5: required-semantics status -> the most an edge may be
_SEM_CAP = {_SEM.CONFIRMED: CONFIRMED, _SEM.UNKNOWN: PROVISIONAL, _SEM.CONTRADICTED: UNHELD}
_NAME = {CONFIRMED: "HELD_CONFIRMED", PROVISIONAL: "HELD_PROVISIONAL", UNHELD: "UNHELD"}

# integral closure mechanism -> the port family that must really exist to back it
_INTEGRAL_SUPPORT = {
    "shoulder_and_head": "planar", "axial_stop": "planar", "retaining_lip": "planar",
    "snap_fit": "planar", "captured_profile": "swept_profile", "dovetail": "swept_profile",
    "press_fit": "cylindrical", "raceway": "cylindrical",
}

# Templates whose INSTANCES are real fasteners (a screw/nut threaded into a receiver).
# A seat's "separate-instance" fastener closure is satisfied ONLY by enough of these.
_FASTENER_TEMPLATES = {
    "screw_into_threaded_receiver", "shoulder_screw_into_tapped_support",
    "shoulder_screw_through_support_with_nut",
}


def _seat_pattern_size(instance, library) -> int:
    """How many fasteners this seat REQUIRES = the largest bound port-group member
    count (an N-hole bolt/bearing pattern needs N screws)."""
    n = 0
    for addr in instance.bindings.values():
        if ":" in addr:
            ref, gid = addr.split(":", 1)
            grp = next((g for g in library.get(ref).port_groups if g.id == gid), None) if ref in library else None
            if grp:
                n = max(n, len(grp.members))
    return n


def _fastener_engages(fi, library, placements) -> bool:
    """A fastener counts toward closure ONLY if it actually engages -- no hard_geometry
    FAIL among its own checks (e.g. thread_engagement: a screw too short to reach/engage
    its receiver does NOT fasten anything, however many instances 'exist')."""
    if library is None or placements is None:
        return True                                  # no poses to judge -> presence only
    try:
        rep = fi.evaluate(library, placements)
    except Exception:
        return True
    return not any(r.verdict == "FAIL" and r.severity == "hard_geometry" for r in rep.results)


def _fasteners_present(instance, all_instances, library=None, placements=None) -> int:
    """How many real fastener instances actually thread into THIS joint's RECEIVER side
    AND engage (right length/thread).

    Scoped to the receiver, NOT to any part of the joint: the bolts that close a
    plate->receiver joint are the ones threading INTO the receiver. (A looser 'any seat
    part' rule wrongly counted the tabletop->cap screws -- which thread into the cap --
    toward the cap->adapter closure, so the cap read 'fastened' with zero real bolts
    into the adapter.) The receiver side = the `to` end of the joint's load-path edges.
    A too-short screw (hard FAIL on thread_engagement) is present-but-not-fastening."""
    recv_refs = set()
    for e in instance.template.load_paths:
        if e.to in instance.bindings:
            recv_refs.add(instance.bindings[e.to].replace(":", ".", 1).split(".", 1)[0])
    if not recv_refs:
        recv_refs = instance.part_refs()
    n = 0
    for fi in all_instances:
        if fi.template.id not in _FASTENER_TEMPLATES:
            continue
        for slot in ("receiver", "support", "nut"):
            if slot in fi.bindings:
                fref = fi.bindings[slot].replace(":", ".", 1).split(".", 1)[0]
                if fref in recv_refs:
                    if _fastener_engages(fi, library, placements):
                        n += 1
                    break
    return n


@dataclass
class Edge:
    frm: str
    to: str
    state: int
    via: str            # instance/template id that produced it
    detail: str = ""


@dataclass
class BodyHold:
    ref: str
    state: int
    path: list = field(default_factory=list)    # list[Edge] frm-body -> ground
    accounted: bool = True                       # False = placed but in NO structural instance

    @property
    def name(self) -> str:
        return "UNACCOUNTED" if not self.accounted else _NAME[self.state]


@dataclass
class LoadPathReport:
    ground: list
    bodies: dict = field(default_factory=dict)   # ref -> BodyHold
    edges: list = field(default_factory=list)

    @property
    def all_confirmed(self) -> bool:
        return all(b.state == CONFIRMED and b.accounted
                   for r, b in self.bodies.items() if r not in self.ground)

    @property
    def unaccounted(self) -> list:
        return sorted(r for r, b in self.bodies.items() if not b.accounted)

    def text(self) -> str:
        lines = [f"LOAD PATH (ground: {sorted(self.ground)}) -> "
                 f"{'ALL HELD_CONFIRMED' if self.all_confirmed else 'NOT all confirmed'}"]
        for ref, b in sorted(self.bodies.items()):
            if ref in self.ground:
                lines.append(f"   {ref:10s} GROUND")
                continue
            if not b.accounted:
                lines.append(f"   {ref:10s} UNACCOUNTED -- placed but in NO structural instance")
                continue
            chain = " -> ".join([e.to for e in b.path]) if b.path else "(no path)"
            lines.append(f"   {ref:10s} {b.name:16s} via {ref} -> {chain}")
            for e in b.path:
                if e.detail:
                    lines.append(f"      edge {e.frm} -> {e.to} via {e.via}: {e.detail}")
        failed = [e for e in self.edges if e.state == UNHELD]
        if failed:
            lines.append("   FAILED EDGES:")
            for e in failed:
                lines.append(f"      {e.frm} -> {e.to} via {e.via}: {e.detail}")
        return "\n".join(lines)


def _closure_state(instance, library, all_instances=(), placements=None) -> tuple[int, str]:
    """Closure for one attachment instance: modeled fastener present, or integral
    geometry really modeled. Returns (state, detail).

    FASTENER ENFORCEMENT (Hard Rule): a closure of kind 'fastener' is satisfied ONLY
    when the actual fastener PART INSTANCES exist. A single bound fastener slot must be
    in the BOM; a 'separate-instance' closure (a bolt/bearing pattern) requires
    count-matched screw/nut instances threading into the seat -- 0 of N => UNHELD (a
    coincident pattern + matching thread is NOT 'fastened' until the screws are real)."""
    states, notes = [], []
    for c in instance.template.closure:
        if c.kind == "fastener":
            slot = c.mechanism
            if slot in instance.bindings:
                ref = instance.bindings[slot].replace(":", ".", 1).split(".", 1)[0]
                if ref in library:
                    states.append(CONFIRMED); notes.append(f"fastener {ref}")
                else:
                    states.append(UNHELD); notes.append(f"fastener {ref} NOT in BOM")
            else:
                # bolt/bearing pattern: count the screw instances that REALLY fill it
                required = _seat_pattern_size(instance, library)
                present = _fasteners_present(instance, all_instances, library, placements)
                if required and present >= required:
                    states.append(CONFIRMED); notes.append(f"fastener '{slot}': {present}/{required} instances")
                elif present > 0:
                    states.append(PROVISIONAL); notes.append(f"fastener '{slot}': only {present}/{required} instances -- INCOMPLETE")
                else:
                    states.append(UNHELD); notes.append(f"fastener '{slot}': 0/{required or '?'} instances -- NOT FASTENED")
        else:  # integral
            fam = _INTEGRAL_SUPPORT.get(c.mechanism)
            found = _confirmed = False
            for ref in instance.part_refs():
                for p in library[ref].ports:
                    if p.family == fam:
                        found = True
                        if p.annotation_status == "confirmed":
                            _confirmed = True
            if _confirmed:
                states.append(CONFIRMED); notes.append(f"integral {c.mechanism} ({fam} port)")
            elif found:
                states.append(PROVISIONAL); notes.append(f"integral {c.mechanism} (nominal port)")
            else:
                states.append(PROVISIONAL); notes.append(f"integral {c.mechanism} ASSERTED (no {fam} port)")
    if not states:
        return CONFIRMED, "no closure required"
    return min(states), "; ".join(notes)


def evaluate(instances, library, placements, ground: list, mode: str = "validation",
             placed=None, non_structural=None) -> LoadPathReport:
    """Build the carried-by graph from all instances' load_paths, grade each edge by
    (its via-checks geometry) AND (its instance closure), then for every body take the
    BEST path to ground (max over paths of the min edge state).

    `placed`: the full set of parts that exist in the assembly (e.g. every render/
    placement ref). EVERY placed part must end up GROUND, HELD, or explicitly listed in
    `non_structural` (a coupling/flexible element with no load-bearing role) -- otherwise
    it is reported UNACCOUNTED and fails the gate. Without this, a part that is placed but
    in NO structural instance is silently invisible to the load-path graph (the motor-on-
    a-belt bug). `non_structural` records the intentional exceptions so they are explicit,
    never silent."""
    edges: list[Edge] = []
    for inst in instances:
        rep = inst.evaluate(library, placements)
        verdict = {r.name: r.verdict for r in rep.results}
        detail_by_name = {r.name: f"{r.verdict} {r.detail}" for r in rep.results}
        cstate, cdetail = _closure_state(inst, library, instances, placements)
        sem, semdetail = _SEM.preflight(inst, library)   # directive Section 4/5
        sstate = _SEM_CAP[sem]
        for e in inst.template.load_paths:
            frm = inst.bindings[e.frm].replace(":", ".", 1).split(".", 1)[0]
            to = inst.bindings[e.to].replace(":", ".", 1).split(".", 1)[0]
            vs = [verdict.get(p) for p in e.via_checks]
            if any(v == "FAIL" for v in vs):
                gstate = UNHELD
            elif any(v in (None, "UNKNOWN") for v in vs):
                gstate = PROVISIONAL
            else:
                gstate = CONFIRMED
            # an edge is CONFIRMED only if geometry PASSes AND closure is real AND the
            # required thread semantics are CONFIRMED -- UNKNOWN/CONTRADICTED cannot
            # create a held edge (Section 5).
            final_state = min(gstate, cstate, sstate)
            if mode == "validation" and final_state < CONFIRMED:
                final_state = UNHELD
            failed_details = [
                f"{p}={detail_by_name.get(p, 'MISSING')}"
                for p, v in zip(e.via_checks, vs)
                if v in (None, "UNKNOWN", "FAIL")
            ]
            failed_text = f"; failed={failed_details}" if failed_details else ""
            edges.append(Edge(frm, to, final_state, inst.template.id,
                              f"checks={dict(zip(e.via_checks, vs))}; closure={cdetail}; "
                              f"semantics={sem}({semdetail}){failed_text}"))

    # adjacency: body -> [(neighbor, edge)]
    adj: dict[str, list] = {}
    bodies = set(ground)
    for e in edges:
        bodies.add(e.frm); bodies.add(e.to)
        if e.state == UNHELD:
            continue
        adj.setdefault(e.frm, []).append(e)

    def best_to_ground(start: str):
        """Max over simple paths of the min edge state; return (state, path)."""
        best = (UNHELD, [])
        stack = [(start, CONFIRMED, [], {start})]
        while stack:
            node, acc, path, seen = stack.pop()
            if node in ground:
                if acc > best[0]:
                    best = (acc, path)
                continue
            for e in adj.get(node, []):
                if e.to in seen:
                    continue
                stack.append((e.to, min(acc, e.state), path + [e], seen | {e.to}))
        return best

    out = LoadPathReport(ground=list(ground), edges=edges)
    for b in bodies:
        if b in ground:
            out.bodies[b] = BodyHold(b, CONFIRMED, [])
        else:
            st, path = best_to_ground(b)
            out.bodies[b] = BodyHold(b, st, path)

    # ACCOUNTING: every placed part must be GROUND, HELD, or a declared coupling.
    # Anything placed but absent from the structural graph is UNACCOUNTED -> fails.
    if placed is not None:
        exempt = set(ground) | set(non_structural or ())
        for ref in placed:
            if ref in out.bodies or ref in exempt:
                continue
            out.bodies[ref] = BodyHold(ref, UNHELD, [], accounted=False)
    return out
