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


# --- v2 bounded value types (manual Section 1.1; migration step A.2) ----------
# These are NOT new top-level ontology classes -- they are the small bounded
# numerical types that live INSIDE engagement ports. Authored in millimetres in a
# part's immutable local frame (glTF stays metres only at the render boundary).

@dataclass
class Interval:
    """A closed bounded scalar range [min, max] in `unit` (default mm)."""
    min: float
    max: float
    unit: str = "mm"

    def __post_init__(self):
        self.min, self.max = float(self.min), float(self.max)
        if self.max < self.min:
            raise ValueError(f"interval max {self.max} < min {self.min}")

    @property
    def span(self) -> float:
        return self.max - self.min

    @property
    def mid(self) -> float:
        return 0.5 * (self.min + self.max)

    def overlap(self, other: "Interval") -> float:
        """Signed overlap length with another interval; negative = a gap."""
        return min(self.max, other.max) - max(self.min, other.min)

    def to_json(self) -> dict:
        return {"min": self.min, "max": self.max, "unit": self.unit}

    @staticmethod
    def from_json(d: dict) -> "Interval":
        return Interval(d["min"], d["max"], d.get("unit", "mm"))


@dataclass
class Measurement:
    """A measured/derived numeric with provenance. Either a `nominal` or a
    bounded min/max; preserves the evidence refs that justify it (Section 3)."""
    nominal: float | None = None
    min: float | None = None
    max: float | None = None
    unit: str = "mm"
    evidence_refs: list = field(default_factory=list)

    def interval(self, default_tol: float = 0.0) -> Interval | None:
        if self.min is not None and self.max is not None:
            return Interval(self.min, self.max, self.unit)
        if self.nominal is not None:
            return Interval(self.nominal - default_tol, self.nominal + default_tol, self.unit)
        return None

    def to_json(self) -> dict:
        return {"nominal": self.nominal, "min": self.min, "max": self.max,
                "unit": self.unit, "evidence_refs": list(self.evidence_refs)}

    @staticmethod
    def from_json(d: dict) -> "Measurement":
        return Measurement(d.get("nominal"), d.get("min"), d.get("max"),
                           d.get("unit", "mm"), d.get("evidence_refs", []))


@dataclass
class LocalFrame:
    """A right-handed coordinate frame inside a part (origin + axes), e.g. the
    section frame of a swept profile or the (u,v) frame of a planar boundary."""
    origin: Vec3 = (0.0, 0.0, 0.0)
    x_axis: Vec3 = (1.0, 0.0, 0.0)
    y_axis: Vec3 = (0.0, 1.0, 0.0)
    z_axis: Vec3 = (0.0, 0.0, 1.0)

    def __post_init__(self):
        self.origin = _v(self.origin)
        self.x_axis = unit(_v(self.x_axis))
        self.y_axis = unit(_v(self.y_axis))
        self.z_axis = unit(_v(self.z_axis))

    def to_json(self) -> dict:
        return {"origin": list(self.origin), "x_axis": list(self.x_axis),
                "y_axis": list(self.y_axis), "z_axis": list(self.z_axis)}

    @staticmethod
    def from_json(d: dict) -> "LocalFrame":
        return LocalFrame(tuple(d.get("origin", (0, 0, 0))),
                          tuple(d.get("x_axis", (1, 0, 0))),
                          tuple(d.get("y_axis", (0, 1, 0))),
                          tuple(d.get("z_axis", (0, 0, 1))))


@dataclass
class Polygon2D:
    """A bounded 2-D region in a declared local (u,v) frame: an outer ring plus
    optional holes. Used for planar boundaries and swept-profile sections -- the
    finite extent that makes a `planar`/`swept_profile` port bounded, not infinite."""
    outer: list = field(default_factory=list)          # [[u,v], ...]
    holes: list = field(default_factory=list)          # [[[u,v], ...], ...]

    def area(self) -> float:
        """Shoelace area of the outer ring minus holes (u,v in mm -> mm^2)."""
        def _ring(r):
            s = 0.0
            for i in range(len(r)):
                u0, v0 = r[i]
                u1, v1 = r[(i + 1) % len(r)]
                s += u0 * v1 - u1 * v0
            return abs(s) * 0.5
        return _ring(self.outer) - sum(_ring(h) for h in self.holes) if self.outer else 0.0

    def to_json(self) -> dict:
        return {"outer": [list(p) for p in self.outer],
                "holes": [[list(p) for p in h] for h in self.holes]}

    @staticmethod
    def from_json(d: dict) -> "Polygon2D":
        return Polygon2D(outer=[tuple(p) for p in d.get("outer", [])],
                         holes=[[tuple(p) for p in h] for h in d.get("holes", [])])


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
