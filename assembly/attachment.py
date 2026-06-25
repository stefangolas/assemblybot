"""Physical-attachment gate (Section 9, strengthens `groundedness`).

The `groundedness` check in validate.py asks only an ABSTRACT question: is the
graph of asserted mate edges connected to one ground? That can pass while a part
sits floating in space, because it never looks at where the parts actually are.

This module asks the PHYSICAL question the manual really wants: pick one anchor
(the single grounded part -- the biggest/base piece) and verify every other body
reaches it through a chain of mates whose mating features are *geometrically
coincident in world space*. An asserted edge only counts if the two features it
names actually touch (faces coplanar & flush; axes collinear) within tolerance.

Convention (parsimony): for Rung 2 every feature's geometry is authored in the
shared assembly/world frame, so no per-part local->world transform is needed yet.
Rung 3's nested moving frames are what will force a real placement transform here
(exactly as Section 4a predicts); add it then, not before.

A failing edge is reported with its measured gap, so a near-miss is debuggable.
A part that reaches the anchor through no verified edge is named as floating.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ontology.primitives import sub, dot, cross, norm, unit


@dataclass
class EdgeCheck:
    a: str            # feature address "p_x.fid"
    b: str
    ctype: str        # constraint type
    attached: bool
    gap_mm: float
    detail: str


@dataclass
class AttachmentResult:
    anchor: str
    reachable: list[str] = field(default_factory=list)
    floating: list[str] = field(default_factory=list)
    edges: list[EdgeCheck] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.floating

    @property
    def detail(self) -> str:
        verified = sum(1 for e in self.edges if e.attached)
        base = (f"anchor {self.anchor!r}: {len(self.reachable)} bodies attached via "
                f"{verified}/{len(self.edges)} geometrically-verified mate(s)")
        if self.floating:
            bad = "; ".join(f"{e.a}-{e.b} gap {e.gap_mm:.1f}mm"
                            for e in self.edges if not e.attached)
            return (f"{base}; FLOATING (no physical path to anchor): "
                    f"{sorted(self.floating)} [broken: {bad}]")
        return base + "; nothing floating"


def _part_ref(addr: str) -> str:
    return addr.split(".", 1)[0]


def _geom(addr: str, library: dict):
    ref, fid = addr.split(".", 1)
    return library[ref].feature(fid).geometry


def _line_line_distance(o1, d1, o2, d2) -> float:
    """Distance between two infinite lines (collinear-axis check)."""
    n = cross(d1, d2)
    nn = norm(n)
    w = sub(o1, o2)
    if nn < 1e-9:                       # parallel -> reject perpendicular component
        proj = dot(w, unit(d1))
        perp = sub(w, tuple(proj * c for c in unit(d1)))
        return norm(perp)
    return abs(dot(w, n)) / nn          # skew lines


def edge_gap(a: str, b: str, ctype: str, library: dict, tol_mm: float):
    """Return (attached, gap_mm, detail) for one mate constraint. The test follows
    the actual GEOMETRY of the two features, not just the declared constraint type
    (a `coplanar` asserted between two axes, or planes whose normals are
    perpendicular, is itself a modeling error and must read as unattached).
    Engagement faces/axes designed to touch read ~0; a misplaced part reads a gap."""
    ga, gb = _geom(a, library), _geom(b, library)
    a_is_axis, b_is_axis = hasattr(ga, "direction"), hasattr(gb, "direction")

    if a_is_axis and b_is_axis:
        # collinear: directions (anti)parallel AND lines coincide
        d1, d2 = unit(ga.direction), unit(gb.direction)
        ang = norm(cross(d1, d2))               # 0 when (anti)parallel
        gap = _line_line_distance(ga.origin, d1, gb.origin, d2)
        ok = ang < 1e-3 and gap <= tol_mm
        return ok, gap, f"axis offset {gap:.2f}mm, dir-cross {ang:.3f}"

    if (not a_is_axis) and (not b_is_axis):
        # coplanar / coincident: faces must be parallel and flush (same plane)
        n1, n2 = unit(ga.normal), unit(gb.normal)
        ang = norm(cross(n1, n2))               # 0 when (anti)parallel normals
        gap = abs(dot(sub(ga.origin, gb.origin), n1))  # distance onto plane a
        ok = ang < 1e-3 and gap <= tol_mm
        return ok, gap, f"face offset {gap:.2f}mm, normal-cross {ang:.3f}"

    # mixed plane<->axis: ill-typed mate. Geometrically the most we can ask is the
    # axis origin lie in the plane; flag the type mismatch loudly.
    plane, axis = (ga, gb) if not a_is_axis else (gb, ga)
    gap = abs(dot(sub(axis.origin, plane.origin), unit(plane.normal)))
    return False, gap, f"TYPE MISMATCH plane<->axis (declared {ctype}); pt-plane {gap:.2f}mm"


def verify_attachment(assembly, library: dict, tol_mm: float = 0.6) -> AttachmentResult:
    """Root at the single grounded part; keep only mate edges whose features are
    geometrically coincident; BFS; report anything that can't reach the anchor."""
    anchor = next(p.ref for p in assembly.parts if p.grounded)
    bodies = {p.ref for p in assembly.parts}

    adj: dict[str, set] = {r: set() for r in bodies}
    edges: list[EdgeCheck] = []
    for m in assembly.mates:
        for c in m.constraints:
            ra, rb = _part_ref(c.a), _part_ref(c.b)
            if ra not in bodies or rb not in bodies or ra == rb:
                continue                          # skip belt (generated, not a body)
            ok, gap, det = edge_gap(c.a, c.b, c.type, library, tol_mm)
            edges.append(EdgeCheck(c.a, c.b, c.type, ok, gap, det))
            if ok:
                adj[ra].add(rb)
                adj[rb].add(ra)

    seen = {anchor}
    stack = [anchor]
    while stack:
        cur = stack.pop()
        for nb in adj[cur]:
            if nb not in seen:
                seen.add(nb)
                stack.append(nb)

    floating = sorted(bodies - seen)
    return AttachmentResult(anchor=anchor, reachable=sorted(seen),
                            floating=floating, edges=edges)
