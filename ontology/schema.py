"""Library + assembly schemas (Section 4f).

These mirror the JSON schemas in the manual verbatim so the library and the
assembly graph stay machine-checkable. geometry and role are kept in separate
fields and never collapsed (Section 5).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional

from .primitives import geometry_from_json
from .roles import assert_role
from .constraints import Constraint, Joint, constraint_from_json, joint_from_json


@dataclass
class Feature:
    """geometry + role + params, kept distinct (Section 4b)."""
    id: str
    geometry: Any  # Point | Axis | Plane
    role: str
    params: dict = field(default_factory=dict)

    def __post_init__(self):
        assert_role(self.role)

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "geometry": self.geometry.to_json(),
            "role": self.role,
            "params": self.params,
        }

    @staticmethod
    def from_json(d: dict) -> "Feature":
        return Feature(
            id=d["id"],
            geometry=geometry_from_json(d["geometry"]),
            role=d["role"],
            params=d.get("params", {}),
        )


@dataclass
class Part:
    """A versioned library entry. The provenance block ties every downstream
    feature back to the page it came from (Section 7)."""
    part_number: str
    cls: str  # serialized as "class"
    source_url: str
    retrieved_at: str
    raw_spec: dict = field(default_factory=dict)
    spec: dict = field(default_factory=dict)
    cad: dict = field(default_factory=dict)
    frame: dict = field(default_factory=lambda: {"origin": [0, 0, 0], "handedness": "right"})
    features: list[Feature] = field(default_factory=list)
    provenance: dict = field(default_factory=lambda: {
        "discovered_by": "manual", "annotated_by": "manual", "confidence": 1.0
    })

    def feature(self, fid: str) -> Feature:
        for f in self.features:
            if f.id == fid:
                return f
        raise KeyError(f"part {self.part_number} has no feature {fid!r}")

    def to_json(self) -> dict:
        return {
            "part_number": self.part_number,
            "class": self.cls,
            "source_url": self.source_url,
            "retrieved_at": self.retrieved_at,
            "raw_spec": self.raw_spec,
            "spec": self.spec,
            "cad": self.cad,
            "frame": self.frame,
            "features": [f.to_json() for f in self.features],
            "provenance": self.provenance,
        }

    @staticmethod
    def from_json(d: dict) -> "Part":
        return Part(
            part_number=d["part_number"],
            cls=d["class"],
            source_url=d["source_url"],
            retrieved_at=d["retrieved_at"],
            raw_spec=d.get("raw_spec", {}),
            spec=d.get("spec", {}),
            cad=d.get("cad", {}),
            frame=d.get("frame", {"origin": [0, 0, 0], "handedness": "right"}),
            features=[Feature.from_json(f) for f in d.get("features", [])],
            provenance=d.get("provenance", {}),
        )


@dataclass
class Mate:
    """interface = bundle of constraints + a joint (Section 4e).

    `couplings` = number of independent kinematic couplings this mate imposes
    beyond its joint (e.g. a belt_drive ties pulley rotation to carriage
    translation). The mobility gate subtracts these (Rung 2)."""
    interface: str
    constraints: list[Constraint]
    joint: Joint
    requires: list[str] = field(default_factory=list)
    couplings: int = 0

    def to_json(self) -> dict:
        return {
            "interface": self.interface,
            "constraints": [c.to_json() for c in self.constraints],
            "joint": self.joint.to_json(),
            "requires": self.requires,
            "couplings": self.couplings,
        }

    @staticmethod
    def from_json(d: dict) -> "Mate":
        return Mate(
            interface=d["interface"],
            constraints=[constraint_from_json(c) for c in d["constraints"]],
            joint=joint_from_json(d["joint"]),
            requires=d.get("requires", []),
            couplings=d.get("couplings", 0),
        )


@dataclass
class PartRef:
    ref: str
    part_number: str
    grounded: bool = False


@dataclass
class Assembly:
    name: str
    parts: list[PartRef] = field(default_factory=list)
    mates: list[Mate] = field(default_factory=list)
    intended_dof: int = 0
    computed_dof: Optional[int] = None
    open_functions: list[str] = field(default_factory=list)

    def to_json(self) -> dict:
        return {
            "name": self.name,
            "parts": [{"ref": p.ref, "part_number": p.part_number, "grounded": p.grounded} for p in self.parts],
            "mates": [m.to_json() for m in self.mates],
            "mobility": {"intended_dof": self.intended_dof, "computed_dof": self.computed_dof},
            "open_functions": self.open_functions,
        }

    def save(self, path: str) -> None:
        with open(path, "w") as fh:
            json.dump(self.to_json(), fh, indent=2)
