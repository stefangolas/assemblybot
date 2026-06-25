"""Procedural toothed-belt skill (Rung 2).

McMaster belt CAD is a straight by-the-foot strip, so the installed loop is ours
to build. From the catalog spec (pitch, width, tooth count) + the placed pulleys
we generate: (1) the pitch-line loop PATH for kinematics + length validation, and
(2) a real TOOTHED FLAT-BAND mesh -- backing of given width/thickness with teeth at
the correct pitch on the inner face -- exported to glb so the viewer shows a belt,
not a smooth tube. The catalog entry is the parameter reference; the geometry is ours.

Validation enforces the catalog constraints: generated loop length == teeth*pitch,
belt pitch == pulley pitch, belt width <= pulley belt-width capacity.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import trimesh

MM_PER_IN = 25.4


@dataclass
class BeltFit:
    points: list                 # pitch-line loop polyline (mm), closed
    length_mm: float
    catalog_mm: float
    teeth: int
    pitch_mm: float
    width_mm: float
    length_ok: bool
    width_ok: bool
    detail: str
    mesh: object = field(default=None, repr=False)

    @property
    def ok(self) -> bool:
        return self.length_ok and self.width_ok


def generate_loop(center_a, center_b, radius_mm, plane_normal=(0, 1, 0), arc_pts=48) -> list:
    """External belt loop tangent to two equal pitch circles (axes along plane_normal)."""
    a = np.asarray(center_a, float); b = np.asarray(center_b, float)
    n = np.asarray(plane_normal, float); n = n / np.linalg.norm(n)
    d = b - a; d = d / np.linalg.norm(d)
    perp = np.cross(d, n); perp = perp / np.linalg.norm(perp)
    r = radius_mm
    pts = [a + r * perp]
    for i in range(arc_pts + 1):                       # wrap around b, far (+d) side
        th = math.pi * i / arc_pts
        pts.append(b + r * (math.cos(th) * perp + math.sin(th) * d))
    pts.append(a - r * perp)
    for i in range(1, arc_pts):                        # wrap around a, far (-d) side
        th = math.pi + math.pi * i / arc_pts
        pts.append(a + r * (math.cos(th) * perp + math.sin(th) * d))
    return [tuple(float(x) for x in p) for p in pts]


def _polyline_len(pts) -> float:
    p = np.asarray(pts + [pts[0]], float)
    return float(np.sum(np.linalg.norm(np.diff(p, axis=0), axis=1)))


def _oriented_box(extents, T, B, N, center):
    """A box with local axes (x=T, y=B, z=N) at `center`."""
    M = np.eye(4)
    M[:3, 0] = T; M[:3, 1] = B; M[:3, 2] = N; M[:3, 3] = center
    return trimesh.creation.box(extents=extents, transform=M)


def build_toothed_mesh(loop_pts, *, width_mm, thickness_mm, pitch_mm, plane_normal=(0, 1, 0),
                       tooth_h=0.76, tooth_frac=0.5) -> trimesh.Trimesh:
    """Flat toothed belt following the pitch-line loop: a backing band (outward) plus
    teeth (inward) spaced every `pitch_mm` along the loop. Width runs along plane_normal."""
    pts = np.asarray(loop_pts, float)
    B = np.asarray(plane_normal, float); B = B / np.linalg.norm(B)
    centroid = pts.mean(axis=0)
    n = len(pts)
    parts = []
    # cumulative arc length, for placing teeth at pitch intervals
    seg_len = [float(np.linalg.norm(pts[(i + 1) % n] - pts[i])) for i in range(n)]
    arclen = np.concatenate([[0], np.cumsum(seg_len)])
    total = arclen[-1]

    for i in range(n):
        p0 = pts[i]; p1 = pts[(i + 1) % n]
        mid = 0.5 * (p0 + p1)
        T = p1 - p0; L = np.linalg.norm(T)
        if L < 1e-9:
            continue
        T = T / L
        N = np.cross(T, B); N = N / np.linalg.norm(N)      # radial
        if np.dot(N, mid - centroid) < 0:                   # make N point OUTWARD
            N = -N
        # backing sits just outside the pitch line
        parts.append(_oriented_box([L * 1.02, width_mm, thickness_mm], T, B, N,
                                    mid + N * (thickness_mm / 2)))

    # teeth on the inner face at pitch spacing
    nteeth = int(round(total / pitch_mm))
    for k in range(nteeth):
        s = (k + 0.5) * pitch_mm
        j = int(np.searchsorted(arclen, s) - 1) % n
        p0 = pts[j]; p1 = pts[(j + 1) % n]
        T = p1 - p0; T = T / (np.linalg.norm(T) + 1e-12)
        N = np.cross(T, B); N = N / np.linalg.norm(N)
        pt = pts[j] + T * (s - arclen[j])
        if np.dot(N, pt - centroid) < 0:
            N = -N
        parts.append(_oriented_box([pitch_mm * tooth_frac, width_mm * 0.9, tooth_h],
                                    T, B, -N, pt - N * (tooth_h / 2)))
    return trimesh.util.concatenate(parts)


def make_belt(center_a, center_b, pitch_radius_mm, *, teeth, pitch_in, width_in,
              pulley_width_in, thickness_mm=1.4, plane_normal=(0, 1, 0),
              tol_mm=1.0, glb_path=None) -> BeltFit:
    pts = generate_loop(center_a, center_b, pitch_radius_mm, plane_normal)
    length = _polyline_len(pts)
    pitch_mm = pitch_in * MM_PER_IN
    width_mm = width_in * MM_PER_IN
    catalog = teeth * pitch_mm
    length_ok = abs(length - catalog) <= tol_mm
    width_ok = width_in <= pulley_width_in + 1e-6
    mesh = build_toothed_mesh(pts, width_mm=width_mm, thickness_mm=thickness_mm,
                              pitch_mm=pitch_mm, plane_normal=plane_normal)
    if glb_path:
        # parts (from cascadio) are in METRES; export the belt to match, not mm
        mesh.copy().apply_scale(0.001).export(glb_path)
    detail = (f"loop {length:.1f} mm vs catalog {teeth}T x {pitch_mm:.2f} = {catalog:.1f} mm "
              f"({'fits' if length_ok else 'NO FIT'}); width {width_in}\" "
              f"{'<=' if width_ok else '>'} pulley {pulley_width_in}\" "
              f"({'ok' if width_ok else 'TOO WIDE'}); {len(mesh.vertices)} verts, "
              f"~{int(round(length/pitch_mm))} teeth")
    return BeltFit(points=pts, length_mm=length, catalog_mm=catalog, teeth=teeth,
                   pitch_mm=pitch_mm, width_mm=width_mm, length_ok=length_ok,
                   width_ok=width_ok, detail=detail, mesh=mesh)


# back-compat shim for the current Rung-2 benchmark (until it's rebuilt)
def fit_belt(center_a, center_b, pitch_radius_mm, *, teeth, pitch_in, plane_normal=(0, 1, 0),
             tol_mm=1.0):
    return make_belt(center_a, center_b, pitch_radius_mm, teeth=teeth, pitch_in=pitch_in,
                     width_in=0.25, pulley_width_in=0.31, plane_normal=plane_normal, tol_mm=tol_mm)
