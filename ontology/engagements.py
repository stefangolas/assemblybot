"""Composable engagement layer for deriving attachment templates.

Engagements are the small generic units between primitive predicates and project
templates. An engagement owns only intrinsic geometry: endpoint port requirements,
pose relation, checks, framed kinematic effect, and load effect. Closure is not an
engagement property; it is derived from the composition that uses the engagements.

Exactness boundary: this engine is exact only for axis-aligned local constraints
expressed in a port's natural frame. Cylindrical ports provide an axis but no clocking
reference; that is acceptable for the symmetric radial/axial freedoms currently in the
catalog. Oblique or coupled constraints, such as conical seats, must not be added to
this catalog without replacing set composition with rank-based constraint algebra.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


DOF = Literal["tx", "ty", "tz", "rx", "ry", "rz"]
ALL_DOF: tuple[DOF, ...] = ("tx", "ty", "tz", "rx", "ry", "rz")


@dataclass(frozen=True)
class EndpointSpec:
    family: str
    polarity: str
    role: str = ""
    is_fastener: bool = False
    optional: bool = False


@dataclass(frozen=True)
class KinematicEffect:
    """Rigid-body freedoms expressed in an engagement-local frame.

    The frame is intentionally named by endpoint slot, not assumed global. A
    cylindrical fit and a planar seat can be perpendicular; composition must preserve
    the frame provenance rather than flattening everything into unframed labels.
    """
    frame_slot: Literal["a", "b"]
    constrained: tuple[DOF, ...] = ()

    @property
    def free(self) -> tuple[DOF, ...]:
        constrained = set(self.constrained)
        return tuple(d for d in ALL_DOF if d not in constrained)


@dataclass(frozen=True)
class LoadEffect:
    """External load transmission capability for a geometric engagement.

    This is deliberately separate from kinematics. Preload or clamp force is not an
    external payload path by itself; it belongs in composition-level closure rules.
    """
    carries: tuple[str, ...] = ()
    excludes: tuple[str, ...] = ()


@dataclass(frozen=True)
class EngagementType:
    id: str
    a: EndpointSpec
    b: EndpointSpec
    relation: str | None
    checks: tuple[str, ...]
    kinematics: KinematicEffect
    load: LoadEffect
    relation_features: tuple[str, str] = ("axis", "axis")


@dataclass(frozen=True)
class EngagementUse:
    engagement_id: str
    a: str
    b: str


@dataclass(frozen=True)
class IntegralClosure:
    mechanism: str
    detail: str = ""


@dataclass(frozen=True)
class FastenerClosure:
    fastener_slot: str
    detail: str = ""


Closure = IntegralClosure | FastenerClosure | None


@dataclass(frozen=True)
class TemplateComposition:
    id: str
    engagements: tuple[EngagementUse, ...]
    closure: Closure = None
    result_override: object | None = None
    participant_roles: dict[str, str] = field(default_factory=dict)
    intended_open: tuple["IntendedFreedom", ...] = ()


@dataclass(frozen=True)
class IntendedFreedom:
    frame_slot: str
    freedoms: tuple[DOF, ...]


@dataclass(frozen=True)
class KinematicSummary:
    constrained_by_frame: dict[str, tuple[DOF, ...]]
    intended_open_violations: tuple[str, ...] = ()


ENGAGEMENTS: dict[str, EngagementType] = {}


def _reg(e: EngagementType) -> EngagementType:
    ENGAGEMENTS[e.id] = e
    return e


_reg(EngagementType(
    id="CYL_FIT",
    a=EndpointSpec("cylindrical", "insert", "cylindrical insert"),
    b=EndpointSpec("cylindrical", "receiver", "cylindrical receiver"),
    relation="coaxial",
    relation_features=("axis", "axis"),
    checks=("radial_fit", "axial_overlap"),
    kinematics=KinematicEffect(
        frame_slot="a",
        constrained=("tx", "ty", "rx", "ry"),
    ),
    load=LoadEffect(carries=("radial_force", "bending_moment")),
))

_reg(EngagementType(
    id="PLANAR_SEAT",
    a=EndpointSpec("planar", "contact", "seated face"),
    b=EndpointSpec("planar", "contact", "supporting face"),
    relation="oppose_and_seat",
    relation_features=("face", "face"),
    checks=("bounded_area_overlap",),
    kinematics=KinematicEffect(
        frame_slot="a",
        constrained=("tz", "rx", "ry"),
    ),
    load=LoadEffect(carries=("axial_force", "overturning_moment")),
))

_reg(EngagementType(
    id="THREAD_MATE",
    a=EndpointSpec("threaded", "external", "external thread", is_fastener=True),
    b=EndpointSpec("threaded", "internal", "internal thread"),
    relation="coaxial",
    relation_features=("axis", "axis"),
    checks=("thread_match", "thread_engagement"),
    kinematics=KinematicEffect(
        frame_slot="a",
        constrained=("tx", "ty", "tz", "rx", "ry"),
    ),
    load=LoadEffect(carries=("axial_force",)),
))

_reg(EngagementType(
    id="HEAD_SEAT",
    a=EndpointSpec("threaded", "external", "screw head underside", is_fastener=True),
    b=EndpointSpec("planar", "contact", "clamped face"),
    relation=None,
    relation_features=("axis", "face"),
    checks=("head_seat",),
    kinematics=KinematicEffect(frame_slot="b", constrained=("tz",)),
    load=LoadEffect(carries=("axial_clamp_reaction",)),
))

_reg(EngagementType(
    id="TIP_CONTACT",
    a=EndpointSpec("threaded", "external", "screw tip or clamp jaw", is_fastener=True),
    b=EndpointSpec("cylindrical", "insert", "cylindrical target"),
    relation=None,
    relation_features=("axis", "axis"),
    checks=("tip_or_clamp_contact",),
    kinematics=KinematicEffect(frame_slot="b", constrained=("tx", "ty")),
    load=LoadEffect(carries=("radial_force",)),
))

_reg(EngagementType(
    id="RACEWAY",
    a=EndpointSpec("cylindrical", "insert", "shaft journal"),
    b=EndpointSpec("cylindrical", "receiver", "bearing race bore"),
    relation="coaxial",
    relation_features=("axis", "axis"),
    checks=("radial_fit", "axial_overlap"),
    kinematics=KinematicEffect(
        frame_slot="a",
        constrained=("tx", "ty", "rx", "ry"),
    ),
    load=LoadEffect(carries=("radial_force", "bending_moment")),
))


def derive_template(comp: TemplateComposition):
    """Derive the legacy AttachmentTemplate shape from an engagement composition."""
    from .templates import (
        AttachmentTemplate,
        Check,
        ClosureRequirement,
        JointSpec,
        LoadPathEdge,
        Participant,
        Relation,
    )

    participants: dict[str, Participant] = {}
    enforce: list[Relation] = []
    checks: list[Check] = []
    load_paths: list[LoadPathEdge] = []

    def add_participant(slot: str, endpoint: EndpointSpec) -> None:
        role = comp.participant_roles.get(slot, endpoint.role)
        existing = participants.get(slot)
        participant = Participant(
            endpoint.family,
            endpoint.polarity,
            role=role,
            is_fastener=endpoint.is_fastener,
            optional=endpoint.optional,
        )
        if existing and (
            existing.family != participant.family
            or existing.polarity != participant.polarity
            or existing.is_fastener != participant.is_fastener
        ):
            raise ValueError(f"{comp.id}: slot {slot!r} has incompatible engagement endpoint requirements")
        participants[slot] = existing or participant

    for use in comp.engagements:
        etype = ENGAGEMENTS[use.engagement_id]
        add_participant(use.a, etype.a)
        add_participant(use.b, etype.b)
        if etype.relation:
            fa, fb = etype.relation_features
            enforce.append(Relation(etype.relation, f"{use.a}.{fa}", f"{use.b}.{fb}"))
        for predicate in etype.checks:
            checks.append(Check(predicate, use.a, use.b))
        if etype.load.carries:
            load_paths.append(LoadPathEdge(use.a, use.b, list(etype.checks)))

    closure = _derive_closure(comp)
    summary = derive_kinematics(comp)
    if summary.intended_open_violations:
        joined = "; ".join(summary.intended_open_violations)
        raise ValueError(f"{comp.id}: intended-open freedom violated by engagement composition: {joined}")
    result = comp.result_override or _derive_result(comp, summary)
    return AttachmentTemplate(
        id=comp.id,
        participants=participants,
        enforce=enforce,
        checks=checks,
        closure=closure,
        load_paths=load_paths,
        result=result,
    )


def _derive_closure(comp: TemplateComposition):
    from .templates import ClosureRequirement

    if comp.closure is None:
        return []
    if isinstance(comp.closure, IntegralClosure):
        return [ClosureRequirement("integral", comp.closure.mechanism, detail=comp.closure.detail)]
    if isinstance(comp.closure, FastenerClosure):
        return [ClosureRequirement("fastener", comp.closure.fastener_slot, detail=comp.closure.detail)]
    raise TypeError(f"{comp.id}: unsupported closure {comp.closure!r}")


def derive_kinematics(comp: TemplateComposition) -> KinematicSummary:
    constrained: dict[str, set[str]] = {}
    for use in comp.engagements:
        etype = ENGAGEMENTS[use.engagement_id]
        frame = use.a if etype.kinematics.frame_slot == "a" else use.b
        constrained.setdefault(frame, set()).update(etype.kinematics.constrained)

    violations: list[str] = []
    for intended in comp.intended_open:
        closed = sorted(set(intended.freedoms) & constrained.get(intended.frame_slot, set()))
        if closed:
            violations.append(f"{intended.frame_slot}: {closed} were intended open")

    return KinematicSummary(
        constrained_by_frame={k: tuple(sorted(v)) for k, v in sorted(constrained.items())},
        intended_open_violations=tuple(violations),
    )


def _derive_result(comp: TemplateComposition, summary: KinematicSummary):
    from .templates import JointSpec

    if isinstance(comp.closure, IntegralClosure):
        if comp.closure.mechanism == "raceway":
            axis_slot = _first_axis_slot(comp, "RACEWAY") or ""
            return JointSpec("revolute", axis_slot=axis_slot)
        if comp.closure.mechanism == "captured_profile":
            return JointSpec("slider")
    return JointSpec("fixed")


def _first_axis_slot(comp: TemplateComposition, engagement_id: str) -> str | None:
    for use in comp.engagements:
        if use.engagement_id == engagement_id:
            return use.a
    return None
