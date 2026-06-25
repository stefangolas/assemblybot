"""Geometric primitives (Section 4a).

Geometry is catalog-independent. Three primitives are implemented; `Path` is
deliberately deferred (Section 4a / Section 10) until belt or gear engagement
forces it. Do not add it here without a ratified failure log.

All coordinates are floats in millimetres, expressed in some part's local frame.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

Vec3 = tuple[float, float, float]

_EPS = 1e-9


def _v(x: Sequence[float]) -> Vec3:
    return (float(x[0]), float(x[1]), float(x[2]))


def sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def scale(a: Vec3, s: float) -> Vec3:
    return (a[0] * s, a[1] * s, a[2] * s)


def dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def norm(a: Vec3) -> float:
    return math.sqrt(dot(a, a))


def unit(a: Vec3) -> Vec3:
    n = norm(a)
    if n < _EPS:
        raise ValueError("cannot normalize a zero-length vector")
    return (a[0] / n, a[1] / n, a[2] / n)


def parallel(a: Vec3, b: Vec3, tol: float = 1e-6) -> bool:
    """True if directions are (anti)parallel."""
    return norm(cross(unit(a), unit(b))) < tol


@dataclass
class Point:
    type: str = field(default="point", init=False)
    position: Vec3 = (0.0, 0.0, 0.0)

    def __post_init__(self):
        self.position = _v(self.position)

    def to_json(self) -> dict:
        return {"type": "point", "position": list(self.position)}


@dataclass
class Axis:
    origin: Vec3 = (0.0, 0.0, 0.0)
    direction: Vec3 = (0.0, 0.0, 1.0)
    type: str = field(default="axis", init=False)

    def __post_init__(self):
        self.origin = _v(self.origin)
        self.direction = unit(_v(self.direction))

    def to_json(self) -> dict:
        return {
            "type": "axis",
            "origin": list(self.origin),
            "direction": list(self.direction),
        }


@dataclass
class Plane:
    origin: Vec3 = (0.0, 0.0, 0.0)
    normal: Vec3 = (0.0, 0.0, 1.0)
    type: str = field(default="plane", init=False)

    def __post_init__(self):
        self.origin = _v(self.origin)
        self.normal = unit(_v(self.normal))

    def to_json(self) -> dict:
        return {
            "type": "plane",
            "origin": list(self.origin),
            "normal": list(self.normal),
        }


@dataclass
class Path:
    """A 1-D routed curve (§4a). RATIFIED at Rung 2 (out/ontology_log/rung2.md) —
    it took a belt to force it, as the manual predicted. Represented as an ordered
    list of points (a polyline; closed if kind ends in '_loop'). Belt loops are
    GENERATED analytically from the pulley pitch circles, never from a catalog mesh."""
    points: list = field(default_factory=list)
    kind: str = "curve"        # e.g. "belt_loop", "pitch_circle"
    closed: bool = False
    type: str = field(default="path", init=False)

    def length(self) -> float:
        pts = self.points + ([self.points[0]] if self.closed and self.points else [])
        return sum(norm(sub(_v(pts[i + 1]), _v(pts[i]))) for i in range(len(pts) - 1))

    def to_json(self) -> dict:
        return {"type": "path", "kind": self.kind, "closed": self.closed,
                "points": [list(p) for p in self.points]}


def geometry_from_json(d: dict):
    t = d["type"]
    if t == "point":
        return Point(position=tuple(d["position"]))
    if t == "axis":
        return Axis(origin=tuple(d["origin"]), direction=tuple(d["direction"]))
    if t == "plane":
        return Plane(origin=tuple(d["origin"]), normal=tuple(d["normal"]))
    if t == "path":
        return Path(points=d.get("points", []), kind=d.get("kind", "curve"),
                    closed=d.get("closed", False))
    raise ValueError(f"unknown geometry type {t!r}")
