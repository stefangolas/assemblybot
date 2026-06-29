"""Attachment templates + instances (Section 6) -- the application's core asset.

An attachment is a small multi-body MECHANISM, not one binary mate. Templates are a
TYPED, DECLARATIVE, SERIALIZABLE registry (user decision): plain dataclasses authored
in Python, deterministic, with `to_json()` as the auditable interchange form. No
lambdas, callbacks, or per-template solver code -- a template only NAMES predicates
and relations; the engine's fixed dispatch tables interpret them.

A template declares, as separate fields (user decision):
  participants -- named slots, each requiring a port FAMILY+POLARITY (or ground);
  enforce      -- pose relations that SOLVE the moving body's placement;
  checks       -- geometric fit predicates (hard_geometry / advisory_engineering);
  closure      -- what removes the residual motion: a modeled FASTENER part, OR
                  INTEGRAL geometry (retaining lip, dovetail, snap, press, raceway,
                  captured profile). Closure is NOT 'a threaded hole is nearby'.
  load_paths   -- the edges that must chain through real parts to ground;
  result       -- the expected joint.

An AttachmentInstance BINDS every slot to a real part_instance.port (or :group).
The defining rule (r6 audit): NO endpoint may be a free world axis/plane -- bind()
rejects any address that is not a bound part. 'coaxial to an abstract axle' is
inexpressible. Closure rigor = a part is HELD only via a continuous path of
instantiated, geometry-checked edges to ground (see ontology.load_path).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import ports_match as PM
from .engagements import EngagementUse, FastenerClosure, IntendedFreedom, IntegralClosure, TemplateComposition, derive_template

# predicate name -> (call-shape, function). Fixed engine dispatch (NOT per-template
# code). Shapes: pair_cyl f(insert,receiver,place_i,place_r); pair_pp f(a,b);
# pair_area f(a,b,place_a,place_b); pair_prof f(insert,receiver);
# group f(defA,grpA,plA,defB,grpB,plB).
_PREDICATES = {
    "radial_fit": ("pair_cyl", PM.radial_fit),
    "axial_overlap": ("pair_cyl", PM.axial_overlap),
    "thread_match": ("pair_pp", PM.thread_match),
    "pitch_profile_match": ("pair_pp", PM.pitch_profile_match),
    "active_width_overlap": ("pair_pp", PM.active_width_overlap),
    "bounded_area_overlap": ("pair_area", PM.bounded_area_overlap),
    "annular_clearance": ("pair_area", PM.annular_clearance),
    "belt_run_seated": ("pair_area", PM.belt_run_seated),
    "profile_containment": ("pair_prof", PM.profile_containment),
    "pattern_correspondence": ("group", PM.pattern_correspondence),
    "coaxial_pattern_correspondence": ("group", PM.coaxial_pattern_correspondence),
    "clearance_pass_through": ("pair_pp", PM.clearance_pass_through),
    "thread_engagement": ("pair_cyl", PM.thread_engagement),
    "head_seat": ("group", PM.head_seat),
    "tip_or_clamp_contact": ("pair_cyl", PM.tip_or_clamp_contact),
}

# enforce relations the pose solver understands (compiled in mate_solver; named here)
_RELATIONS = {"coaxial", "coplanar", "coincident", "distance", "angle", "tangent",
             "oppose_and_seat"}

# integral closure mechanisms (when closure is geometry, not a separate fastener)
_INTEGRAL_CLOSURES = {"retaining_lip", "dovetail", "snap_fit", "press_fit",
                      "raceway", "captured_profile", "axial_stop", "shoulder_and_head"}


@dataclass
class JointSpec:
    type: str = "fixed"                  # fixed | revolute | slider | screw
    axis_slot: str = ""                  # participant whose port axis is the joint axis

    def __post_init__(self):
        if self.type not in ("fixed", "revolute", "slider", "screw"):
            raise ValueError(f"JointSpec: bad type {self.type!r}")

    def to_json(self) -> dict:
        return {"type": self.type, "axis_slot": self.axis_slot}


@dataclass
class Participant:
    family: str | None = None
    polarity: str | None = None
    role: str = ""
    is_fastener: bool = False            # must be a real modeled retaining part
    optional: bool = False              # may be left unbound (e.g. a bearing face we add later)

    def to_json(self) -> dict:
        return {"family": self.family, "polarity": self.polarity,
                "role": self.role, "is_fastener": self.is_fastener,
                "optional": self.optional}


@dataclass
class Relation:
    """A pose-enforcing relation between two participant port addresses."""
    type: str
    a: str
    b: str
    value: float | None = None

    def __post_init__(self):
        if self.type not in _RELATIONS:
            raise ValueError(f"Relation: {self.type!r} not in {sorted(_RELATIONS)}")

    def to_json(self) -> dict:
        d = {"type": self.type, "a": self.a, "b": self.b}
        if self.value is not None:
            d["value"] = self.value
        return d


@dataclass
class Check:
    predicate: str
    a: str
    b: str = ""
    severity: str = "hard_geometry"      # hard_geometry | advisory_engineering

    def __post_init__(self):
        if self.predicate not in _PREDICATES:
            raise ValueError(f"unknown predicate {self.predicate!r}")
        if self.severity not in ("hard_geometry", "advisory_engineering"):
            raise ValueError(f"Check: bad severity {self.severity!r}")

    def to_json(self) -> dict:
        return {"predicate": self.predicate, "a": self.a, "b": self.b, "severity": self.severity}


@dataclass
class ClosureRequirement:
    """What removes the joint's residual translation/rotation. Either a modeled
    fastener participant, or named integral geometry. Evaluated by the load-path
    gate; a bare 'threaded hole nearby' is NOT acceptable closure."""
    kind: str                            # "fastener" | "integral"
    mechanism: str = ""                  # fastener slot name, or an _INTEGRAL_CLOSURES key
    via: str = ""                        # supporting port address(es), informational
    detail: str = ""

    def __post_init__(self):
        if self.kind not in ("fastener", "integral"):
            raise ValueError(f"ClosureRequirement: bad kind {self.kind!r}")
        if self.kind == "integral" and self.mechanism not in _INTEGRAL_CLOSURES:
            raise ValueError(f"ClosureRequirement: integral mechanism {self.mechanism!r} "
                             f"not in {sorted(_INTEGRAL_CLOSURES)}")

    def to_json(self) -> dict:
        return {"kind": self.kind, "mechanism": self.mechanism, "via": self.via, "detail": self.detail}


@dataclass
class SemanticClaim:
    """A required semantic claim that must be confirmed by evidence."""
    slot: str
    claims: list = field(default_factory=list)

    def to_json(self) -> dict:
        return {"slot": self.slot, "claims": list(self.claims)}


@dataclass
class LoadPathEdge:
    """A required edge of the path to ground: body `frm` is carried by body `to`
    through the named checks. The assembly gate chains these to a grounded part."""
    frm: str
    to: str
    via_checks: list = field(default_factory=list)   # predicate names that must PASS

    def to_json(self) -> dict:
        return {"frm": self.frm, "to": self.to, "via_checks": list(self.via_checks)}


@dataclass
class AttachmentTemplate:
    id: str
    participants: dict                   # name -> Participant
    enforce: list = field(default_factory=list)    # list[Relation]
    checks: list = field(default_factory=list)     # list[Check]
    closure: list = field(default_factory=list)    # list[ClosureRequirement]
    load_paths: list = field(default_factory=list) # list[LoadPathEdge]
    required_semantics: list = field(default_factory=list) # list[SemanticClaim]
    result: JointSpec = field(default_factory=JointSpec)

    def fastener_slots(self) -> list:
        return [n for n, p in self.participants.items() if p.is_fastener]

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "participants": {n: p.to_json() for n, p in self.participants.items()},
            "enforce": [r.to_json() for r in self.enforce],
            "checks": [c.to_json() for c in self.checks],
            "closure": [c.to_json() for c in self.closure],
            "load_paths": [e.to_json() for e in self.load_paths],
            "required_semantics": [s.to_json() for s in self.required_semantics],
            "result": self.result.to_json(),
        }

    def bind(self, bindings: dict) -> "AttachmentInstance":
        """bindings: slot -> 'p_ref.port' | 'p_ref:group' | 'GROUND'. Rejects unbound
        slots and any non-ground endpoint that is not a real part address (the ban on
        free world-axis endpoints)."""
        for name, part in self.participants.items():
            if name not in bindings:
                if getattr(part, "optional", False):
                    continue                       # optional slot may be left unbound
                raise ValueError(f"template {self.id}: participant {name!r} unbound")
            addr = bindings[name]
            if addr == "GROUND":
                raise ValueError(f"template {self.id}: slot {name!r} bound to GROUND (GROUND is not a part)")
            if "." not in addr and ":" not in addr:
                raise ValueError(f"template {self.id}: slot {name!r} -> {addr!r} is not a real "
                                 f"part.port/:group address (free endpoints are BANNED)")
        return AttachmentInstance(self, dict(bindings))


# ---- instance + evaluation ----------------------------------------------------

@dataclass
class AttachmentReport:
    template: str
    results: list = field(default_factory=list)     # list[PredicateResult]
    state: str = "unknown"               # confirmed|nominally_compatible|incomplete|unknown|contradicted
    joint: str = "fixed"

    def text(self) -> str:
        lines = [f"[{self.template}] -> {self.state.upper()} (joint: {self.joint})"]
        for r in self.results:
            lines.append("   " + str(r))
        return "\n".join(lines)


@dataclass
class AttachmentInstance:
    template: AttachmentTemplate
    bindings: dict

    def part_refs(self) -> set:
        out = set()
        for slot, addr in self.bindings.items():
            if addr != "GROUND":
                out.add(addr.replace(":", ".", 1).split(".", 1)[0])
        return out

    def fastener_refs(self) -> list:
        return [self.bindings[s].replace(":", ".", 1).split(".", 1)[0]
                for s in self.template.fastener_slots()]

    def _resolve(self, slot_addr: str, library, placements):
        addr = self.bindings.get(slot_addr, slot_addr)
        ref, _, ident = addr.replace(":", ".", 1).partition(".")
        part, place = library[ref], placements[ref]
        is_group = ":" in addr
        obj = (next(g for g in part.port_groups if g.id == ident) if is_group
               else part.port(ident))
        return part, obj, place

    def evaluate(self, library, placements) -> AttachmentReport:
        """Run every fit Check at the solved poses (closure is the load-path gate's
        job, reported separately)."""
        out = []
        for chk in self.template.checks:
            kind, fn = _PREDICATES[chk.predicate]
            # skip a check that references an OPTIONAL participant left unbound (e.g. a
            # head_seat with no bearing face bound yet) -- it isn't applicable, not a failure.
            if any(s in self.template.participants
                   and getattr(self.template.participants[s], "optional", False)
                   and s not in self.bindings for s in (chk.a, chk.b)):
                continue
            try:
                pa, oa, pla = self._resolve(chk.a, library, placements)
                pb, ob, plb = self._resolve(chk.b, library, placements)
            except Exception as e:
                out.append(PM.PredicateResult(chk.predicate, "UNKNOWN", "required_closure", {}, f"resolution failed: {e}"))
                continue

            if kind == "pair_pp":
                out.append(fn(oa, ob))
            elif kind in ("pair_cyl", "pair_area"):
                out.append(fn(oa, ob, pla, plb))
            elif kind == "pair_prof":
                out.append(fn(oa, ob))
            elif kind == "group":
                out.append(fn(pa, oa, pla, pb, ob, plb))
        return AttachmentReport(self.template.id, out, _overall_state(out),
                                self.template.result.type)


def _overall_state(results) -> str:
    """Section 5 attachment states from per-check verdicts (fit checks only)."""
    hard = [r for r in results if r.severity == "hard_geometry"]
    if any(r.verdict == "FAIL" for r in hard):
        return "contradicted"
    closure = [r for r in results if r.severity == "required_closure"]
    if any(r.verdict in ("UNKNOWN", "FAIL") for r in closure):
        return "incomplete"
    if any(r.verdict == "UNKNOWN" for r in hard):
        return "unknown"
    return "confirmed"


# ============================================================================
# REGISTRY -- only the templates the current rungs + neighbors need (Section B).
# No catalog-specific templates; 'T-slot nut' stays a recipe, not a template.
# ============================================================================

TEMPLATES: dict[str, AttachmentTemplate] = {}


def _reg(t: AttachmentTemplate) -> AttachmentTemplate:
    TEMPLATES[t.id] = t
    return t


_reg(AttachmentTemplate(
    id="retained_revolute_on_journal",
    participants={
        "rotor": Participant("cylindrical", "receiver", role="rotating bore"),
        "journal": Participant("cylindrical", "insert", role="shaft/shoulder", is_fastener=True),
    },
    enforce=[Relation("coaxial", "rotor.axis", "journal.axis")],
    checks=[Check("radial_fit", "journal", "rotor"),
            Check("axial_overlap", "journal", "rotor")],
    closure=[ClosureRequirement("integral", "shoulder_and_head",
                                detail="shoulder seats the bore axially; screw head retains the far side")],
    # within-mechanism edge only: the bore rides the shoulder. The journal (screw)
    # reaching ground is a SEPARATE screw_into_threaded_receiver instance.
    load_paths=[LoadPathEdge("rotor", "journal", ["radial_fit", "axial_overlap"])],
    result=JointSpec("revolute", axis_slot="journal"),
))

# --- r9 SPLIT (directive Section 3): pose/fit, retention, and screw-to-support are
#     SEPARATE concepts. A local bearing/journal fit PASS must NEVER imply the support
#     attachment passes. Use these instead of the monolithic template above.

_reg(AttachmentTemplate(
    id="revolute_fit_on_journal",
    participants={
        "rotor": Participant("cylindrical", "receiver", role="rotating bore / bearing inner race"),
        "journal": Participant("cylindrical", "insert", role="shaft/shoulder"),
    },
    enforce=[Relation("coaxial", "rotor.axis", "journal.axis")],
    checks=[Check("radial_fit", "journal", "rotor"),
            Check("axial_overlap", "journal", "rotor")],
    closure=[],          # KINEMATIC RELATION ONLY -- not a held joint
    load_paths=[],       # creates NO load-path edge (pose/fit, not attachment)
    result=JointSpec("revolute", axis_slot="journal"),
))

_reg(AttachmentTemplate(
    id="fixed_hub_on_journal",
    participants={
        # A pulley/pinion bore clamped onto a motor shaft, turning WITH it (not a revolute).
        "hub": Participant("cylindrical", "receiver", role="hub/pinion bore"),
        "journal": Participant("cylindrical", "insert", role="motor shaft / journal"),
        # Closure is a real radial set screw bearing on the shaft flat -- NOT integral.
        # Hard Rule 6: a set-screw closure needs a real modeled set-screw PART; until that
        # part + its radial thread port are bound, the hub reads PROVISIONAL/UNHELD.
        "set_screw": Participant("threaded", "external", role="radial set screw onto shaft", is_fastener=True),
    },
    enforce=[Relation("coaxial", "hub.axis", "journal.axis")],
    checks=[Check("radial_fit", "journal", "hub"),
            Check("axial_overlap", "journal", "hub")],
    closure=[ClosureRequirement("fastener", "set_screw",
                                detail="radial set screw clamps the bore onto the shaft flat")],
    load_paths=[
        LoadPathEdge("hub", "journal", ["radial_fit", "axial_overlap"]),
        LoadPathEdge("set_screw", "hub", []),
    ],
    result=JointSpec("fixed"),
))

_reg(derive_template(TemplateComposition(
    id="radial_screw_against_cylindrical_target",
    engagements=(
        EngagementUse("CYL_FIT", "target", "body_bore", reverse_load=True),
        EngagementUse("THREAD_MATE", "screw", "thread"),
        EngagementUse("TIP_CONTACT", "screw", "target"),
    ),
    closure=FastenerClosure("screw", "radial screw threads through body and contacts target"),
    participant_roles={
        "body_bore": "body bore around cylindrical target",
        "target": "shaft/journal/cylindrical clamped target",
        "screw": "radial clamp or set screw",
        "thread": "radial threaded hole in the clamping body",
    },
)))

_reg(derive_template(TemplateComposition(
    id="clamp_keyed_hub_on_journal",
    engagements=(
        EngagementUse("CYL_FIT", "journal", "hub", reverse_load=True),
        EngagementUse("TIP_CONTACT", "clamp_fastener", "journal"),
    ),
    closure=FastenerClosure("clamp_fastener", "clamp/keyed hub fastener provides torque-retaining closure"),
    participant_roles={
        "hub": "clamp/keyed hub bore",
        "journal": "shaft journal",
        "clamp_fastener": "clamp screw or keyed-hub retainer",
    },
)))

_reg(derive_template(TemplateComposition(
    id="pilot_clamped_hub_to_carrier",
    engagements=(
        EngagementUse("CYL_FIT", "pilot", "hub", reverse_load=True),
        EngagementUse("PLANAR_SEAT", "hub_seat", "seat"),
        EngagementUse("HEAD_SEAT", "clamp_fastener", "hub_seat"),
    ),
    closure=FastenerClosure("clamp_fastener", "pulley is clamped to the carrier flange by real screws"),
    participant_roles={
        "hub": "pulley pilot bore",
        "pilot": "carrier locating pilot",
        "hub_seat": "pulley mounting face",
        "seat": "carrier flange face",
        "clamp_fastener": "pulley-to-carrier screw",
    },
)))

_reg(AttachmentTemplate(
    id="inner_race_axial_retention",
    participants={
        "rotor": Participant("cylindrical", "receiver", role="bearing INNER race (recessed)"),
        "journal": Participant("cylindrical", "insert", role="shoulder the race clamps onto"),
        "spacer_a": Participant("planar", "contact", role="shim: support-side race face", is_fastener=True),
        "spacer_b": Participant("planar", "contact", role="shim: head-side race face", is_fastener=True),
    },
    enforce=[Relation("coaxial", "rotor.axis", "journal.axis")],
    checks=[Check("radial_fit", "journal", "rotor"),
            Check("axial_overlap", "journal", "rotor")],
    # closure = the modeled shim stack clamps the RECESSED inner race (not the rotating
    # flange). Until the shims are real PartInstances this stays provisional/unheld.
    closure=[ClosureRequirement("fastener", "spacer_a", detail="shim clamps the recessed race, support side"),
             ClosureRequirement("fastener", "spacer_b", detail="shim clamps the recessed race, head side")],
    load_paths=[LoadPathEdge("rotor", "journal", ["radial_fit", "axial_overlap"])],
    result=JointSpec("revolute", axis_slot="journal"),
))

_reg(AttachmentTemplate(
    id="shoulder_screw_into_tapped_support",
    participants={
        "screw": Participant("threaded", "external", role="shoulder screw thread", is_fastener=True),
        "support": Participant("threaded", "internal", role="tapped support (the tap IS the closure)"),
    },
    enforce=[Relation("coaxial", "screw.axis", "support.axis")],
    checks=[Check("thread_match", "screw", "support")],
    closure=[ClosureRequirement("fastener", "screw", detail="screw threaded into a confirmed tapped hole")],
    load_paths=[LoadPathEdge("screw", "support", ["thread_match"])],
    required_semantics=[SemanticClaim("support", ["hole_type", "thread_designation"])],
    result=JointSpec("fixed"),
))

_reg(AttachmentTemplate(
    id="shoulder_screw_through_support_with_nut",
    participants={
        "screw": Participant("threaded", "external", role="screw through a clearance hole", is_fastener=True),
        "support": Participant("cylindrical", "receiver", role="support with a CLEARANCE hole"),
        "nut": Participant("threaded", "internal", role="real nut providing closure", is_fastener=True),
    },
    enforce=[Relation("coaxial", "screw.axis", "support.axis")],
    # the screw must pass the clearance hole AND thread-match a REAL nut (the closure).
    checks=[Check("clearance_pass_through", "screw", "support"),
            Check("thread_match", "screw", "nut")],
    closure=[ClosureRequirement("fastener", "nut", detail="a real modeled nut clamps the support")],
    load_paths=[LoadPathEdge("screw", "support", ["clearance_pass_through", "thread_match"])],
    required_semantics=[SemanticClaim("support", ["hole_type", "bore_diameter"])],
    result=JointSpec("fixed"),
))

_reg(AttachmentTemplate(
    id="screw_into_threaded_receiver",
    participants={
        "screw": Participant("threaded", "external", role="fastener", is_fastener=True),
        "receiver": Participant("threaded", "internal", role="tapped hole"),
        # the clamped face the cap underside seats on -- bind it to enforce head seating.
        "bearing": Participant("planar", "contact", role="clamped face under the cap",
                               optional=True),
    },
    enforce=[Relation("coaxial", "screw.axis", "receiver.axis")],
    checks=[Check("thread_match", "screw", "receiver"),
            Check("thread_engagement", "screw", "receiver"),
            Check("head_seat", "screw", "bearing")],   # runs only when `bearing` is bound   # reach + min engagement at the placed poses
    closure=[ClosureRequirement("fastener", "screw", detail="the screw IS the closure")],
    # head_seat is part of the load path: a cap not seated on the clamped face is not
    # truly fastening (skipped -> provisional until a bearing face is bound; FAIL -> UNHELD).
    load_paths=[LoadPathEdge("screw", "receiver",
                             ["thread_match", "thread_engagement", "head_seat"])],
    result=JointSpec("fixed"),
))

_reg(AttachmentTemplate(
    id="bounded_bolt_pattern_seat",
    participants={
        "plate": Participant("planar", "contact", role="mounted plate + hole group"),
        "seat": Participant("planar", "contact", role="acceptor seat + tapped group"),
    },
    enforce=[Relation("oppose_and_seat", "plate.face", "seat.face")],
    checks=[Check("pattern_correspondence", "plate_group", "seat_group"),
            Check("bounded_area_overlap", "plate", "seat")],
    closure=[ClosureRequirement("fastener", "screws",
                                detail="screws filling the matched pattern (separate instances)")],
    load_paths=[LoadPathEdge("plate", "seat", ["pattern_correspondence", "bounded_area_overlap"])],
    result=JointSpec("fixed"),
))

_reg(AttachmentTemplate(
    id="through_bolted_plate",
    # A plate clamped to a threaded receiver by through-bolts that SPAN a spacer/stack
    # (e.g. a cap bolted to a base through a sandwiched pulley). The two bolt patterns are
    # coaxial + same PCD but axially offset by the stack thickness, so coincidence is
    # checked in the plane perpendicular to the bolt axis (coaxial_pattern_correspondence).
    participants={
        "plate": Participant("planar", "contact", role="plate clamped by through-bolts"),
        "receiver": Participant("planar", "contact", role="threaded receiver across the stack"),
    },
    enforce=[],                                # placed analytically; the bolts set the clamp
    checks=[Check("coaxial_pattern_correspondence", "plate_group", "receiver_group")],
    closure=[ClosureRequirement("fastener", "bolts",
                                detail="through-bolts clamp the plate to the receiver across the stack (separate instances)")],
    load_paths=[LoadPathEdge("plate", "receiver", ["coaxial_pattern_correspondence"])],
    result=JointSpec("fixed"),
))

_reg(AttachmentTemplate(
    id="profile_carriage_on_guide",
    participants={
        "carriage": Participant("swept_profile", "receiver", role="guide block"),
        "guide": Participant("swept_profile", "insert", role="rail"),
    },
    enforce=[Relation("coaxial", "carriage.sweep", "guide.sweep")],
    checks=[Check("profile_containment", "guide", "carriage")],
    closure=[ClosureRequirement("integral", "captured_profile",
                                detail="ball-bearing recirculation captures the rail profile")],
    load_paths=[LoadPathEdge("carriage", "guide", ["profile_containment"])],
    result=JointSpec("slider"),
))

_reg(AttachmentTemplate(
    id="timing_belt_mesh",
    participants={
        "belt": Participant("periodic", "opposing", role="belt toothed side"),
        "pulley": Participant("periodic", "external", role="pulley/idler teeth"),
    },
    enforce=[Relation("tangent", "belt.support", "pulley.support")],
    checks=[Check("pitch_profile_match", "belt", "pulley"),
            Check("active_width_overlap", "belt", "pulley", "advisory_engineering")],
    closure=[],                          # mesh is a coupling, not a held joint
    load_paths=[],
    required_semantics=[SemanticClaim("belt", ["pitch", "profile", "active_width"]),
                        SemanticClaim("pulley", ["pitch", "profile", "active_width"])],
    result=JointSpec("fixed"),
))

_reg(derive_template(TemplateComposition(
    id="fastened_face_mount",
    engagements=(
        EngagementUse("PLANAR_SEAT", "mounted", "support"),
        EngagementUse("THREAD_MATE", "fastener", "receiver"),
        EngagementUse("HEAD_SEAT", "fastener", "mounted"),
    ),
    closure=FastenerClosure("fastener", "modeled mounting fastener provides closure"),
    participant_roles={
        "mounted": "mounted face",
        "support": "supporting face",
        "fastener": "mounting screw",
        "receiver": "threaded receiver or nut that the mounting screw engages",
    },
)))

_reg(derive_template(TemplateComposition(
    id="journal_supported_by_bearing",
    engagements=(EngagementUse("RACEWAY", "journal", "bearing"),),
    closure=IntegralClosure("raceway", "bearing raceway supports the shaft radially"),
    intended_open=(IntendedFreedom("journal", ("rz",)),),
    participant_roles={
        "journal": "shaft journal",
        "bearing": "bearing inner bore",
    },
)))

_reg(AttachmentTemplate(
    id="tslot_captured_mount",
    participants={
        "mounted": Participant("planar", "contact", role="part foot seated on the extrusion face"),
        "slot": Participant("swept_profile", "receiver", role="extrusion T-slot (continuous domain)"),
        "nut": Participant("swept_profile", "insert", role="T-slot nut captured in the slot", is_fastener=True),
    },
    # the nut slides ANYWHERE along the slot (continuous placement domain), so the
    # pose is set by seating the foot on the slot face; the clamp force is a SEPARATE
    # screw_into_threaded_receiver instance (screw -> nut thread), per split-templates.
    enforce=[Relation("oppose_and_seat", "mounted.face", "slot.face")],
    checks=[Check("profile_containment", "nut", "slot")],
    closure=[ClosureRequirement("integral", "captured_profile",
                                detail="the nut's profile is captured by the slot lips; a separate clamp "
                                       "screw (screw_into_threaded_receiver) into the nut provides the force")],
    load_paths=[LoadPathEdge("mounted", "slot", ["profile_containment"])],
    required_semantics=[SemanticClaim("slot", ["profile_identity", "capture_geometry"]),
                        SemanticClaim("nut", ["profile_identity"])],
    result=JointSpec("fixed"),
))

_reg(AttachmentTemplate(
    id="bearing_ring_mount",
    # rung-3: a plate (clearance-counterbored holes) bolts to ONE ring of a
    # crossed-roller bearing and MUST stay clear of the other ring. Used twice:
    # base -> outer ring, rotating adapter -> inner ring. The race-segregation
    # (annular_clearance vs the forbidden ring) is the deciding new check.
    participants={
        "plate": Participant("planar", "contact", role="mounting face with clearance-hole group"),
        "ring": Participant("planar", "contact", role="the bearing ring face this plate bolts to (tapped)"),
        "forbidden": Participant("planar", "contact", role="the OTHER ring face -- must NOT be touched"),
    },
    enforce=[Relation("oppose_and_seat", "plate.face", "ring.face")],
    checks=[Check("pattern_correspondence", "plate_group", "ring_group"),
            Check("bounded_area_overlap", "plate", "ring"),
            Check("annular_clearance", "plate", "forbidden")],   # race-segregation (NEW)
    closure=[ClosureRequirement("fastener", "screws",
                                detail="M5 screws filling the matched ring pattern (separate instances)")],
    load_paths=[LoadPathEdge("plate", "ring",
                             ["pattern_correspondence", "bounded_area_overlap", "annular_clearance"])],
    result=JointSpec("fixed"),
))

_reg(AttachmentTemplate(
    id="pilot_located_bolted_hub",
    # rung-3: a pulley/hub is LOCATED concentric by a cylindrical pilot (radial_fit),
    # seated on a planar face, and CLAMPED by a bolt pattern. The pilot establishes
    # concentricity; the bolts only clamp -- a real locate-vs-clamp distinction.
    participants={
        "hub": Participant("cylindrical", "receiver", role="pulley bore"),
        "pilot": Participant("cylindrical", "insert", role="locating pilot on the carrier"),
        "hub_seat": Participant("planar", "contact", role="pulley underside seating face"),
        "seat": Participant("planar", "contact", role="carrier seat face the pulley lands on"),
    },
    enforce=[Relation("coaxial", "hub.axis", "pilot.axis")],
    checks=[Check("radial_fit", "pilot", "hub"),                 # pilot LOCATES (h6/H7)
            Check("bounded_area_overlap", "hub_seat", "seat"),   # seats flush
            Check("pattern_correspondence", "hub_group", "seat_group")],  # bolts CLAMP
    closure=[ClosureRequirement("fastener", "screws",
                                detail="M5 screws through the pulley holes into the carrier (separate instances)")],
    load_paths=[LoadPathEdge("hub", "pilot", ["radial_fit", "bounded_area_overlap", "pattern_correspondence"])],
    result=JointSpec("fixed"),
))

_reg(AttachmentTemplate(
    id="pilot_located_through_bolted_hub",
    # A pilot-located hub/pulley clamped by through-bolts across a finite stack.
    # The bore pilot and seated face are flush, but the clearance-hole group and
    # tapped receiver group live on different axial planes, so compare the
    # pattern projected along the bolt axis.
    participants={
        "hub": Participant("cylindrical", "receiver", role="pulley bore"),
        "pilot": Participant("cylindrical", "insert", role="locating pilot on the carrier"),
        "hub_seat": Participant("planar", "contact", role="pulley seating face"),
        "seat": Participant("planar", "contact", role="carrier seat face the pulley lands on"),
    },
    enforce=[Relation("coaxial", "hub.axis", "pilot.axis")],
    checks=[Check("radial_fit", "pilot", "hub"),
            Check("bounded_area_overlap", "hub_seat", "seat"),
            Check("coaxial_pattern_correspondence", "hub_group", "seat_group")],
    closure=[ClosureRequirement("fastener", "screws",
                                detail="M5 screws through the pulley holes into the carrier")],
    load_paths=[LoadPathEdge("hub", "pilot",
                             ["radial_fit", "bounded_area_overlap", "coaxial_pattern_correspondence"])],
    result=JointSpec("fixed"),
))

_reg(AttachmentTemplate(
    id="crossed_roller_revolute",
    # rung-3: the bearing's INTERNAL revolute (inner ring rotates vs outer ring),
    # closed by the integral raceway. This is the machine's one output DOF.
    participants={
        "inner": Participant("cylindrical", "receiver", role="rotating inner ring bore"),
        "outer": Participant("cylindrical", "receiver", role="stationary outer ring"),
    },
    enforce=[Relation("coaxial", "inner.axis", "outer.axis")],
    checks=[],                                   # catalog subassembly: internal fit is given
    closure=[ClosureRequirement("integral", "raceway",
                                detail="crossed-roller raceway carries radial+axial+moment load, 1 DOF free")],
    load_paths=[LoadPathEdge("inner", "outer", [])],
    result=JointSpec("revolute", axis_slot="outer"),
))

_reg(AttachmentTemplate(
    id="belt_capture",
    # MINIMAL belt-clamp constraint set -- a belt clamp is UNDERCONSTRAINED (and thus
    # not really verified) without ALL of these. The earlier version checked only tooth
    # compatibility, so a carriage parked with its grip 90 mm off the belt still
    # "passed". A belt clamp must pin down: WHERE the teeth catch, WHICH WAY they run,
    # how WIDE the engagement is, and that a real opposing jaw sandwiches the belt.
    participants={
        "belt": Participant("periodic", "opposing", role="belt run"),
        "grip": Participant("periodic", "opposing", role="toothed clamp face the belt seats on (load-bearing backing)"),
        "jaw": Participant("periodic", "opposing", role="opposing toothed jaw sandwiching the belt", is_fastener=True),
        "grip_group": Participant("repeated_ports", "receiver", role="clearance holes on the grip part"),
        "jaw_group": Participant("repeated_ports", "internal", role="tapped holes on the jaw"),
    },
    enforce=[Relation("oppose_and_seat", "grip.support", "belt.support"),
             Relation("oppose_and_seat", "jaw.support", "belt.support")],
    checks=[Check("pitch_profile_match", "belt", "grip"),                 # teeth MESH
            Check("belt_run_seated", "belt", "grip"),                    # WHERE + WHICH WAY (placement-dependent, hard)
            Check("active_width_overlap", "belt", "grip", "advisory_engineering")],  # width contained
    closure=[ClosureRequirement("fastener", "jaw",
                                detail="opposing toothed jaw sandwiches the belt -- must be a real part")],
    # the hold is real only if the teeth mesh AND the run actually seats on the grip in
    # world space (pose), not merely if the profiles are compatible.
    load_paths=[LoadPathEdge("belt", "grip", ["pitch_profile_match", "belt_run_seated"])],
    result=JointSpec("fixed"),
))
