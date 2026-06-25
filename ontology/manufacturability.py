"""Part-level manufacturability / minimum-material gate (DFM) -- judges a SINGLE part's
own geometry, independent of any assembly.

Why this exists (the Oe160 cap): the 4x M6 tabletop taps sat at R77.8 on a Oe160 (R80)
disc -> the hole edge (R80.8) ran PAST the part edge. No assembly attachment check sees
this: pattern_correspondence/thread_engagement all passed, because the defect is intrinsic
to the part, not the joint. A hole hanging off the edge is a defect as real as a floating
fastener -- so we need a part-intrinsic gate, like a DFM rule, run when a (especially
custom/generated) part is authored.

v1 checks, against the part's largest bounded planar face (assumed normal to local Z;
other orientations -> UNKNOWN for now):
  - hole-to-edge material  >= max(floor, min_factor * hole_diameter)
  - hole-to-hole material  >= floor
Holes = cylindrical receivers (radius = radial max) and internal threads (radius = major/2).
"""
from __future__ import annotations
import re
import numpy as np
from shapely.geometry import Polygon, Point

from .ports_match import PredicateResult


def _major_mm(thread: dict):
    md = thread.get("major_diameter_mm")
    if isinstance(md, dict):
        return float(md.get("max") or md.get("min"))
    m = re.match(r"\s*M(\d+(?:\.\d+)?)", thread.get("designation", "") or "")
    return float(m.group(1)) if m else None


def _holes(part_def):
    """[(id, x, y, radius)] for every hole-like port, in the part-local frame."""
    out = []
    for p in part_def.ports:
        g = p.geometry
        if p.family == "cylindrical" and p.polarity == "receiver":
            r = g["radial_interval_mm"]["max"]; o = g["axis"]["origin"]
        elif p.family == "threaded" and p.polarity == "internal":
            mj = _major_mm(g.get("thread", {})); r = mj / 2 if mj else None; o = g["axis"]["origin"]
        else:
            continue
        out.append((p.id, float(o[0]), float(o[1]), r))
    return out


def edge_distance(part_def, *, min_factor: float = 0.75, floor_mm: float = 2.0):
    """Return a list of PredicateResult, one per hole, for hole-to-edge material, plus a
    summary. min_factor*D is the required material from hole edge to part edge (rule of
    thumb ~0.75-1xD for the wall; raise for soft alloy or high load)."""
    faces = [p for p in part_def.ports
             if p.family == "planar" and "boundary_uv_mm" in p.geometry
             and abs(np.asarray(p.geometry["plane"]["normal"], float)[2]) > 0.9]
    if not faces:
        return [PredicateResult("edge_distance", "UNKNOWN", "advisory_engineering",
                                detail="no Z-normal bounded face to measure against")]
    poly = max((Polygon(f.geometry["boundary_uv_mm"]["outer"]) for f in faces), key=lambda q: q.area)
    results = []
    for (hid, x, y, r) in _holes(part_def):
        if r is None:
            results.append(PredicateResult("edge_distance", "UNKNOWN", "advisory_engineering",
                                           {"hole": hid}, f"{hid}: unknown radius")); continue
        pt = Point(x, y)
        d = poly.exterior.distance(pt)
        material = round(d - r, 2)
        # k*D is a bolt tear-out rule -> a fastener-scale concern; cap D at ~M12 so a big
        # central bore is judged on wall thickness (the floor), not an absurd k*94 mm.
        need = round(max(floor_mm, min_factor * 2 * min(r, 6.0)), 2)
        m = {"hole": hid, "center_to_edge_mm": round(d, 2), "hole_r_mm": r,
             "edge_material_mm": material, "required_mm": need,
             "inside_face": poly.contains(pt)}
        if not poly.contains(pt) or material < 0:
            v, sev = "FAIL", "hard_geometry"
            note = f"{hid}: hole RUNS OFF the part edge (material {material} mm)"
        elif material < need:
            v, sev = "FAIL", "hard_geometry"
            note = f"{hid}: only {material} mm to edge, need >= {need} mm (~{min_factor}xD)"
        else:
            v, sev = "PASS", "advisory_engineering"
            note = f"{hid}: {material} mm edge material (>= {need})"
        results.append(PredicateResult("edge_distance", v, sev, m, note))
    return results


def check_part(part_def, **kw):
    """Convenience: True/False + the failing holes."""
    res = edge_distance(part_def, **kw)
    fails = [r for r in res if r.verdict == "FAIL"]
    return (not fails), res
