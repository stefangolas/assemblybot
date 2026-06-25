"""The Assembly Agent ontology (Section 4).

Deliberately small: three geometric primitives, a flat role vocabulary, six
constraints, four joints. It grows only via ratified failure logs (Section 10).
"""
from .primitives import Point, Axis, Plane, Path, geometry_from_json
from .roles import ROLES, assert_role
from .constraints import Constraint, Joint, CONSTRAINT_TYPES, JOINT_DOF
from .schema import Feature, Part, Mate, PartRef, Assembly

__all__ = [
    "Point", "Axis", "Plane", "Path", "geometry_from_json",
    "ROLES", "assert_role",
    "Constraint", "Joint", "CONSTRAINT_TYPES", "JOINT_DOF",
    "Feature", "Part", "Mate", "PartRef", "Assembly",
]
