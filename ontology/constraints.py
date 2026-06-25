"""Constraints and kinematic joints (Sections 4c, 4d).

Six constraint relations cover the overwhelming majority of machinery. The one
dynamic relation, `motion`, resolves to a kinematic joint. The solver works at
the constraint level; we reason and report at the interface level (Section 4e).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# Section 4c -- the six relations. `motion` is the only dynamic one.
CONSTRAINT_TYPES = {
    "coincident",  # two points share a position
    "coaxial",     # two axes share a line  -- the workhorse
    "coplanar",    # two planes coincide
    "distance",    # fixed separation
    "angle",       # fixed orientation
    "motion",      # the one dynamic relation -> resolves to a joint
}

# Section 4d -- the four kinematic joint types and their nominal DOF (spatial).
JOINT_DOF = {
    "fixed": 0,
    "revolute": 1,   # one rotation
    "slider": 1,     # one translation (prismatic)
    "screw": 1,      # coupled rotation+translation, 1 independent coordinate
}


@dataclass
class Constraint:
    """A relation between two named features, addressed as 'part_ref.feature_id'."""
    type: str
    a: str
    b: str
    value: Optional[float] = None  # for distance (mm) / angle (deg)

    def __post_init__(self):
        if self.type not in CONSTRAINT_TYPES:
            raise ValueError(
                f"constraint type {self.type!r} not in ontology {sorted(CONSTRAINT_TYPES)}. "
                f"Do not improvise -- log a failure + minimal extension (Section 10)."
            )
        if self.type in ("distance", "angle") and self.value is None:
            raise ValueError(f"{self.type} constraint requires a `value`")

    def to_json(self) -> dict:
        d = {"type": self.type, "a": self.a, "b": self.b}
        if self.value is not None:
            d["value"] = self.value
        return d


@dataclass
class Joint:
    type: str
    axis: Optional[str] = None  # feature ref naming the joint axis
    coupling: Optional[dict] = None  # e.g. {"to": other_joint, "ratio": pitch_radius}

    def __post_init__(self):
        if self.type not in JOINT_DOF:
            raise ValueError(f"joint type {self.type!r} not in {sorted(JOINT_DOF)}")

    @property
    def dof(self) -> int:
        return JOINT_DOF[self.type]

    def to_json(self) -> dict:
        d = {"type": self.type}
        if self.axis is not None:
            d["axis"] = self.axis
        if self.coupling is not None:
            d["coupling"] = self.coupling
        return d


def constraint_from_json(d: dict) -> Constraint:
    return Constraint(type=d["type"], a=d["a"], b=d["b"], value=d.get("value"))


def joint_from_json(d: dict) -> Joint:
    return Joint(type=d["type"], axis=d.get("axis"), coupling=d.get("coupling"))
