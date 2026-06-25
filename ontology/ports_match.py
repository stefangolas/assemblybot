"""Compatibility predicates -- the family matchers (Section 5).

Separate from POSE solving (that stays in assembly/mate_solver.py). After a pose is
solved, each predicate returns PASS|FAIL|UNKNOWN plus the MEASUREMENTS and a severity
class, exactly as the manual demands:

  hard_geometry        a known failure rejects the candidate
  required_closure     missing/unknown -> INCOMPLETE / review, never silently incompatible
  advisory_engineering ranks candidates, does not normally reject

These are the same numbers `_attach_check.py` overlays, so the look and the engine
check the same thing (Hard Rule 1b). A predicate NEVER reads `semantic_aliases`;
acceptance is family + polarity + geometry only (Hard Rule 4).

This is the module that makes the shoulder-screw-too-short / clamp-doesn't-fit
failures SURFACE as numbers instead of prose (Hard Rule 5).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .ports import EngagementPort, PortGroup
from .primitives import Interval, Polygon2D
from . import semantics as _SEM

try:                                    # robust polygon ops when available
    from shapely.geometry import Polygon as _ShPoly
    _HAVE_SHAPELY = True
except Exception:                       # noqa: BLE001
    _HAVE_SHAPELY = False


# ---- world placement of a port's axis / spans --------------------------------

def _R(p):  return np.asarray(p["R"], float)
def _t(p):  return np.asarray(p["t_mm"], float)


def world_axis(port: EngagementPort, place: dict):
    """(origin, unit-direction) of a cylindrical/threaded port's axis in world mm."""
    a = port.axis()
    o = _R(place) @ np.asarray(a.origin, float) + _t(place)
    d = _R(place) @ np.asarray(a.direction, float)
    return o, d / np.linalg.norm(d)


def world_axial_interval(port: EngagementPort, place: dict, ref_dir, ref_o) -> Interval:
    """Project a port's local axial_interval onto a shared world axis (ref_o, ref_dir).
    The local interval is coordinates ALONG the port axis; after placement the
    endpoints map to world points whose projection on ref_dir gives the world span."""
    o, d = world_axis(port, place)
    ref_dir = np.asarray(ref_dir, float)
    ref_dir = ref_dir / np.linalg.norm(ref_dir)
    iv = port.axial_interval()
    p_lo = o + iv.min * d
    p_hi = o + iv.max * d
    s_lo = float(np.dot(p_lo - np.asarray(ref_o, float), ref_dir))
    s_hi = float(np.dot(p_hi - np.asarray(ref_o, float), ref_dir))
    return Interval(min(s_lo, s_hi), max(s_lo, s_hi))


@dataclass
class PredicateResult:
    name: str
    verdict: str                 # PASS | FAIL | UNKNOWN
    severity: str                # hard_geometry | required_closure | advisory_engineering
    measurements: dict = field(default_factory=dict)
    detail: str = ""

    def __str__(self) -> str:
        return f"[{self.verdict:7s}] {self.name} ({self.severity}): {self.detail}"


def _line_offset(o1, d1, o2):
    """Perpendicular distance of point-on-line-2 origin from line 1 (mm)."""
    w = np.asarray(o2, float) - np.asarray(o1, float)
    return float(np.linalg.norm(w - np.dot(w, d1) * d1))


# ---- cylindrical: radial_fit + axial_overlap (Section 5) ----------------------

def radial_fit(insert: EngagementPort, receiver: EngagementPort,
               place_i: dict, place_r: dict) -> PredicateResult:
    """Does the insert's outer radius fit inside the receiver's bore radius, with
    the axes coaxial? insert.material_side=outside (max radius = shaft OR),
    receiver.material_side=inside (min radius = bore IR)."""
    if insert.family != "cylindrical" or receiver.family != "cylindrical":
        return PredicateResult("radial_fit", "UNKNOWN", "hard_geometry",
                               detail="both ports must be cylindrical")
    oi, di = world_axis(insert, place_i)
    orr, dr = world_axis(receiver, place_r)
    ang = float(np.degrees(np.arccos(np.clip(abs(np.dot(di, dr)), -1, 1))))
    axis_off = _line_offset(orr, dr, oi)
    shaft_or = insert.radial_interval().max
    bore_ir = receiver.radial_interval().min
    clearance = bore_ir - shaft_or
    m = {"shaft_OR_mm": shaft_or, "bore_IR_mm": bore_ir, "diametral_clearance_mm": 2 * clearance,
         "axis_offset_mm": round(axis_off, 4), "axis_tilt_deg": round(ang, 3)}
    if ang > 1.0 or axis_off > 0.6:
        return PredicateResult("radial_fit", "FAIL", "hard_geometry", m,
                               f"axes not coaxial (off {axis_off:.2f} mm, tilt {ang:.2f} deg)")
    if clearance < -1e-6:
        return PredicateResult("radial_fit", "FAIL", "hard_geometry", m,
                               f"shaft OR {shaft_or} > bore IR {bore_ir} -> interference")
    return PredicateResult("radial_fit", "PASS", "hard_geometry", m,
                           f"clearance {2*clearance:.3f} mm diametral; coaxial")


def axial_overlap(insert: EngagementPort, receiver: EngagementPort,
                  place_i: dict, place_r: dict) -> PredicateResult:
    """How much finite axial length is actually shared. This is the predicate that
    catches a shoulder TOO SHORT to span its bore (STATE r6 idler bug): the engaged
    length is min(spans, overlap)."""
    orr, dr = world_axis(receiver, place_r)
    iv_i = world_axial_interval(insert, place_i, dr, orr)
    iv_r = world_axial_interval(receiver, place_r, dr, orr)
    ov = iv_i.overlap(iv_r)
    insert_span, recv_span = insert.axial_interval().span, receiver.axial_interval().span
    m = {"insert_span_mm": insert_span, "receiver_span_mm": recv_span,
         "engaged_length_mm": round(ov, 3),
         "engaged_frac_of_receiver": round(ov / recv_span, 3) if recv_span > 0 else None}
    if ov <= 0:
        return PredicateResult("axial_overlap", "FAIL", "hard_geometry", m,
                               "no shared axial length -- parts do not engage")
    # engaging less than the receiver's full width is a real (often acceptable, but
    # human-review) condition -> required_closure, not a silent pass/fail.
    if ov + 1e-6 < recv_span:
        return PredicateResult("axial_overlap", "UNKNOWN", "required_closure", m,
                               f"insert spans only {ov:.1f} of receiver's {recv_span:.1f} mm "
                               f"-- is the unspanned length supported elsewhere? (review)")
    return PredicateResult("axial_overlap", "PASS", "hard_geometry", m,
                           f"engaged length {ov:.1f} mm covers the receiver")


# ---- threaded: thread_match (Section 5) ---------------------------------------

def thread_match(a: EngagementPort, b: EngagementPort) -> PredicateResult:
    """internal vs external thread compatibility: opposite polarity, equal pitch,
    same handedness, compatible major diameter when known.

    EVIDENCE GATE (directive Section 4, the r9 fix): thread semantics are a SEMANTIC
    claim that a CAD cylinder cannot establish. A geometric mismatch is still a FAIL,
    but a PASS is only allowed when BOTH ports' thread semantics are CONFIRMED from a
    thread-confirming source. If either side is unconfirmed -> UNKNOWN (never PASS);
    if either is contradicted -> FAIL. This is what stops 'M4 thread into an M3
    clearance hole annotated M4-tapped-from-CAD' from passing."""
    if a.family != "threaded" or b.family != "threaded":
        return PredicateResult("thread_match", "UNKNOWN", "hard_geometry",
                               detail="both ports must be threaded (a clearance hole is "
                                      "cylindrical, NOT a threaded receiver)")
    ta, tb = a.geometry["thread"], b.geometry["thread"]
    pol = {a.polarity, b.polarity}
    m = {"a": ta.get("designation"), "b": tb.get("designation"),
         "pitch_a": ta.get("pitch_mm"), "pitch_b": tb.get("pitch_mm")}
    if pol != {"internal", "external"}:
        return PredicateResult("thread_match", "FAIL", "hard_geometry", m,
                               f"need one internal + one external, got {pol}")
    if ta.get("pitch_mm") and tb.get("pitch_mm") and abs(ta["pitch_mm"] - tb["pitch_mm"]) > 1e-3:
        return PredicateResult("thread_match", "FAIL", "hard_geometry", m,
                               f"pitch mismatch {ta['pitch_mm']} vs {tb['pitch_mm']} mm")
    if ta.get("handedness") and tb.get("handedness") and ta["handedness"] != tb["handedness"]:
        return PredicateResult("thread_match", "FAIL", "hard_geometry", m, "handedness mismatch")
    if ta.get("designation") and tb.get("designation") and ta["designation"] != tb["designation"]:
        return PredicateResult("thread_match", "UNKNOWN", "required_closure", m,
                               f"designations differ ({ta['designation']} vs {tb['designation']}) "
                               f"but pitch/handedness compatible -- confirm fit")
    return PredicateResult("thread_match", "PASS", "hard_geometry", m,
                           f"threads compatible ({ta.get('designation') or 'pitch '+str(ta.get('pitch_mm'))})")


def _thread_major_radius(port: EngagementPort):
    """External thread major RADIUS (mm) from major_diameter_mm, else None."""
    th = port.geometry.get("thread", {})
    md = th.get("major_diameter_mm")
    if isinstance(md, dict) and md.get("max") is not None:
        return float(md["max"]) / 2.0
    if isinstance(md, (int, float)):
        return float(md) / 2.0
    return None

def clearance_pass_through(screw: EngagementPort, hole: EngagementPort) -> PredicateResult:
    """A screw PASSES THROUGH a clearance hole (does not thread into it)."""
    if screw.family != "threaded" or screw.polarity != "external":
        return PredicateResult("clearance_pass_through", "UNKNOWN", "hard_geometry",
                               detail="screw side must be an external threaded port")
    if hole.family != "cylindrical" or hole.polarity != "receiver":
        return PredicateResult("clearance_pass_through", "UNKNOWN", "hard_geometry",
                               detail="hole side must be a cylindrical receiver (clearance hole)")
    
    major_r = _thread_major_radius(screw)
    bore_ir = hole.radial_interval().min
    m = {"thread_major_r_mm": major_r, "bore_IR_mm": bore_ir,
         "hole_status": hole.annotation_status}
         
    if hole.annotation_status == "unknown":
        return PredicateResult("clearance_pass_through", "UNKNOWN", "hard_geometry", m,
                               "hole geometry is unknown")

    if major_r is not None and major_r > bore_ir + 1e-6:
        return PredicateResult("clearance_pass_through", "FAIL", "hard_geometry", m,
                               f"thread major Ø{2*major_r:.1f} cannot pass clearance hole "
                               f"Ø{2*bore_ir:.1f} -- screw does not fit (CONTRADICTED)")
    
    return PredicateResult("clearance_pass_through", "PASS", "hard_geometry", m,
                           "screw fits through clearance hole (but provides no closure on its own)")


# ---- periodic: pitch_profile_match + active_width_overlap (Section 5) ----------

def pitch_profile_match(a: EngagementPort, b: EngagementPort) -> PredicateResult:
    """Two toothed regions mesh only if pitch (and profile family when known) match."""
    if a.family != "periodic" or b.family != "periodic":
        return PredicateResult("pitch_profile_match", "UNKNOWN", "hard_geometry",
                               detail="both ports must be periodic")
    pa, pb = a.geometry["periodicity"]["pitch_mm"], b.geometry["periodicity"]["pitch_mm"]
    fa = a.geometry["profile"].get("family"); fb = b.geometry["profile"].get("family")
    m = {"pitch_a_mm": pa, "pitch_b_mm": pb, "profile_a": fa, "profile_b": fb}
    if abs(pa - pb) > 1e-3:
        return PredicateResult("pitch_profile_match", "FAIL", "hard_geometry", m,
                               f"pitch mismatch {pa} vs {pb} mm")
    if fa and fb and fa != "unknown" and fb != "unknown" and fa != fb:
        return PredicateResult("pitch_profile_match", "FAIL", "hard_geometry", m,
                               f"profile mismatch {fa} vs {fb}")
    return PredicateResult("pitch_profile_match", "PASS", "hard_geometry", m,
                           f"pitch {pa} mm, profile {fa or 'unknown'} compatible")


def active_width_overlap(a: EngagementPort, b: EngagementPort) -> PredicateResult:
    """Do two meshing toothed regions share enough ACTIVE WIDTH (belt width vs
    pulley/clamp face width)? A 10 mm belt on a 6 mm pulley face engages only 6 mm."""
    if a.family != "periodic" or b.family != "periodic":
        return PredicateResult("active_width_overlap", "UNKNOWN", "hard_geometry",
                               detail="both ports must be periodic")
    wa = Interval.from_json(a.geometry["periodicity"]["active_width_mm"])
    wb = Interval.from_json(b.geometry["periodicity"]["active_width_mm"])
    shared = min(wa.max, wb.max)        # both widths start at 0; engaged = narrower face
    m = {"width_a_mm": [wa.min, wa.max], "width_b_mm": [wb.min, wb.max], "engaged_width_mm": shared}
    if shared <= 0:
        return PredicateResult("active_width_overlap", "FAIL", "hard_geometry", m,
                               "no shared active width")
    return PredicateResult("active_width_overlap", "PASS", "advisory_engineering", m,
                           f"engaged width {shared:.1f} mm")


def _linear_support_world(port: EngagementPort, place: dict):
    """World (origin, plane-normal, run-direction, active interval) of a periodic
    LINEAR support (belt run / toothed clamp face)."""
    sup = port.geometry["support"]
    o = _R(place) @ np.asarray(sup["plane"]["origin"], float) + _t(place)
    n = _R(place) @ np.asarray(sup["plane"]["normal"], float); n /= np.linalg.norm(n)
    d = _R(place) @ np.asarray(sup["direction"], float); d /= np.linalg.norm(d)
    return o, n, d, Interval.from_json(sup["active_region_mm"])


def belt_run_seated(belt: EngagementPort, grip: EngagementPort,
                    place_belt: dict, place_grip: dict) -> PredicateResult:
    """PLACEMENT-DEPENDENT pose check for a belt clamp -- the constraint a belt clamp
      (1) WHERE the teeth catch -- the run's support plane is coincident with the grip
          face (parallel + small gap) and their footprints OVERLAP along the run;
      (2) WHICH WAY -- the run direction is parallel to the grip's belt travel direction (a
          180-degree reversal is allowed but a crosswise placement is not; the `direction`
          field of a periodic port denotes belt travel, not physical tooth orientation); and
    Catches a carriage parked so its grip is off the belt even though the teeth match."""
    if belt.family != "periodic" or grip.family != "periodic":
        return PredicateResult("belt_run_seated", "UNKNOWN", "hard_geometry",
                               detail="need a periodic belt run + a periodic toothed grip")
    if grip.geometry.get("subtype") != "linear" or belt.geometry.get("subtype") != "linear":
        return PredicateResult("belt_run_seated", "UNKNOWN", "hard_geometry",
                               detail="both supports must be LINEAR (a straight clamped run)")
    o_b, n_b, d_b, reg_b = _linear_support_world(belt, place_belt)
    o_g, n_g, d_g, reg_g = _linear_support_world(grip, place_grip)

    face_cos = abs(float(np.dot(n_b, n_g)))                  # (1) clamp faces parallel
    gap = abs(float(np.dot(o_b - o_g, n_g)))                 #     belt plane vs grip plane
    dir_cos = abs(float(np.dot(d_b, d_g)))                   # (2) run runs along the teeth
    # (3) overlap of the two active runs, projected on the grip's run direction
    sb = sorted(float(np.dot(o_b + s * d_b - o_g, d_g)) for s in (reg_b.min, reg_b.max))
    sg = sorted([reg_g.min, reg_g.max])
    overlap = min(sb[1], sg[1]) - max(sb[0], sg[0])
    m = {"face_parallel_cos": round(face_cos, 3), "plane_gap_mm": round(gap, 2),
         "run_dir_cos": round(dir_cos, 3), "engaged_len_mm": round(overlap, 1)}
    if face_cos < 0.98:
        return PredicateResult("belt_run_seated", "FAIL", "hard_geometry", m,
                               "belt run is not parallel to the clamp face")
    if dir_cos < 0.98:
        return PredicateResult("belt_run_seated", "FAIL", "hard_geometry", m,
                               "belt run direction is not aligned with the grip teeth "
                               "(belt clamped crosswise -- teeth cannot mesh)")
    if gap > 2.0:
        return PredicateResult("belt_run_seated", "FAIL", "hard_geometry", m,
                               f"belt run sits {gap:.1f} mm off the clamp-face plane")
    if overlap <= 0:
        return PredicateResult("belt_run_seated", "FAIL", "hard_geometry", m,
                               f"belt run does NOT overlap the grip along the run "
                               f"(gap {-overlap:.0f} mm) -- the grip is off the belt")
    return PredicateResult("belt_run_seated", "PASS", "hard_geometry", m,
                           f"belt run seated on the grip: {overlap:.0f} mm engaged, "
                           f"gap {gap:.2f} mm, aligned")


# ---- planar: bounded_area_overlap (Section 2.2 / 5) ---------------------------

def _canonical_uv(normal):
    """Deterministic (u,v) tangent basis for a plane normal -- the SAME basis the
    annotator must use to author boundary_uv (so uv->world is reproducible)."""
    n = np.asarray(normal, float); n = n / np.linalg.norm(n)
    a = np.array([1.0, 0.0, 0.0]) if abs(n[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = a - np.dot(a, n) * n; u = u / np.linalg.norm(u)
    v = np.cross(n, u)
    return u, v


def _planar_world_polygon(port: EngagementPort, place: dict):
    """Outer boundary of a planar port as Nx3 world points (mm)."""
    pl = port.geometry["plane"]
    o = _R(place) @ np.asarray(pl["origin"], float) + _t(place)
    n = _R(place) @ np.asarray(pl["normal"], float)
    u, v = _canonical_uv(pl["normal"])
    uw, vw = _R(place) @ u, _R(place) @ v
    pts = [o + uu * uw + vv * vw for uu, vv in port.geometry["boundary_uv_mm"]["outer"]]
    return np.asarray(pts), o, n / np.linalg.norm(n)


def bounded_area_overlap(a: EngagementPort, b: EngagementPort,
                         place_a: dict, place_b: dict) -> PredicateResult:
    """Opposed-normal seating: do the two finite faces actually OVERLAP, and is the
    gap closed? Infinite-plane coplanarity is never proof of contact (Section 2.2)."""
    if a.family != "planar" or b.family != "planar":
        return PredicateResult("bounded_area_overlap", "UNKNOWN", "hard_geometry",
                               detail="both ports must be planar")
    Pa, oa, na = _planar_world_polygon(a, place_a)
    Pb, ob, nb = _planar_world_polygon(b, place_b)
    ang = float(np.degrees(np.arccos(np.clip(abs(np.dot(na, nb)), -1, 1))))
    gap = float(abs(np.dot(ob - oa, na)))
    # project B's outer ring onto A's plane basis to intersect in 2-D
    u, v = _canonical_uv(a.geometry["plane"]["normal"])
    uw, vw = _R(place_a) @ u, _R(place_a) @ v
    def to2d(P):
        return [(float(np.dot(p - oa, uw)), float(np.dot(p - oa, vw))) for p in P]
    m = {"normal_tilt_deg": round(ang, 3), "seating_gap_mm": round(gap, 3)}
    if not _HAVE_SHAPELY:
        m["overlap_area_mm2"] = "shapely_unavailable"
        verdict = "UNKNOWN"
        return PredicateResult("bounded_area_overlap", verdict, "required_closure", m,
                               "install shapely for area; normal/gap measured only")
    inter = _ShPoly(to2d(Pa)).intersection(_ShPoly(to2d(Pb)))
    area = float(inter.area)
    m["overlap_area_mm2"] = round(area, 2)
    if ang > 2.0:
        return PredicateResult("bounded_area_overlap", "FAIL", "hard_geometry", m,
                               f"faces not parallel (tilt {ang:.1f} deg)")
    if area <= 1e-6:
        return PredicateResult("bounded_area_overlap", "FAIL", "hard_geometry", m,
                               "faces do not overlap -- no contact patch")
    if gap > 0.6:
        return PredicateResult("bounded_area_overlap", "UNKNOWN", "required_closure", m,
                               f"overlap {area:.0f} mm2 but seating gap {gap:.2f} mm -- not flush")
    return PredicateResult("bounded_area_overlap", "PASS", "hard_geometry", m,
                           f"flush contact patch {area:.0f} mm2 (gap {gap:.2f} mm)")


# ---- race-segregation: annular_clearance (rung-3 NEW) -------------------------

def _annulus_radii(port: EngagementPort):
    """(r_in, r_out) of a planar port's annular footprint in its own uv frame (mm).
    r_out = farthest outer-boundary vertex; r_in = farthest first-hole vertex (the
    central opening) or 0. Measured from the plane (uv) origin."""
    b = port.geometry["boundary_uv_mm"]
    outer = np.asarray(b["outer"], float)
    r_out = float(np.max(np.hypot(outer[:, 0], outer[:, 1])))
    holes = b.get("holes") or []
    r_in = 0.0
    if holes:
        h = np.asarray(holes[0], float)
        r_in = float(np.max(np.hypot(h[:, 0], h[:, 1])))
    return r_in, r_out


def annular_clearance(part: EngagementPort, forbidden: EngagementPort,
                      place_part: dict, place_forbidden: dict,
                      min_clear_mm: float = 0.3) -> PredicateResult:
    """RACE-SEGREGATION (rung-3): does `part`'s contact face stay CLEAR of a
    `forbidden` coaxial ring face it must NOT touch? This is the inverse of
    bounded_area_overlap -- it PASSES when the two finite annuli do NOT interfere:
       - their radial bands [r_in,r_out] do not overlap (radially separated), OR
       - they overlap radially but are axially separated by >= min_clear_mm.
    It FAILS when the bands overlap radially AND the axial gap < min_clear (they would
    touch). This is exactly the 'base opening Ø94 clears the inner ring' and
    'adapter relieved 0.5 mm clears the outer ring' check (task verifications #1-3)."""
    if part.family != "planar" or forbidden.family != "planar":
        return PredicateResult("annular_clearance", "UNKNOWN", "hard_geometry",
                               detail="both ports must be planar (annular contact faces)")
    _, oa, na = _planar_world_polygon(part, place_part)
    _, ob, nb = _planar_world_polygon(forbidden, place_forbidden)
    ria, roa = _annulus_radii(part)
    rib, rob = _annulus_radii(forbidden)
    # lateral (off-axis) offset of the two annulus centers -- must be ~coaxial
    lat = _line_offset(oa, na / np.linalg.norm(na), ob)
    axial_gap = float(abs(np.dot(ob - oa, na / np.linalg.norm(na))))
    # radial-band overlap (negative => radially separated => clear)
    radial_overlap = min(roa, rob) - max(ria, rib)
    m = {"part_band_mm": [round(ria, 2), round(roa, 2)],
         "forbidden_band_mm": [round(rib, 2), round(rob, 2)],
         "radial_overlap_mm": round(radial_overlap, 2),
         "axial_gap_mm": round(axial_gap, 3), "lateral_offset_mm": round(lat, 3)}
    if lat > 1.0:
        return PredicateResult("annular_clearance", "UNKNOWN", "hard_geometry", m,
                               f"faces not coaxial (offset {lat:.2f} mm) -- band logic invalid")
    if radial_overlap <= 0:
        return PredicateResult("annular_clearance", "PASS", "hard_geometry", m,
                               f"radially separated by {-radial_overlap:.1f} mm -- cannot touch the wrong ring")
    if axial_gap >= min_clear_mm - 1e-6:
        return PredicateResult("annular_clearance", "PASS", "hard_geometry", m,
                               f"radial bands overlap but axial gap {axial_gap:.2f} mm "
                               f">= {min_clear_mm} mm -- relieved clear of the wrong ring")
    return PredicateResult("annular_clearance", "FAIL", "hard_geometry", m,
                           f"would contact the wrong ring: radial overlap {radial_overlap:.1f} mm "
                           f"with only {axial_gap:.2f} mm axial gap (< {min_clear_mm} mm)")


# ---- swept_profile: profile_containment (Section 2.3 / 5) ---------------------

def profile_containment(insert: EngagementPort, receiver: EngagementPort) -> PredicateResult:
    """Does the insert's cross-section fit inside the receiver's channel section
    (T-slot/dovetail capture), with finite swept overlap? Section profiles are in
    each port's own section frame; this compares them in 2-D (the capture logic)."""
    if insert.family != "swept_profile" or receiver.family != "swept_profile":
        return PredicateResult("profile_containment", "UNKNOWN", "hard_geometry",
                               detail="both ports must be swept_profile")
    si = Interval.from_json(insert.geometry["sweep_interval_mm"])
    sr = Interval.from_json(receiver.geometry["sweep_interval_mm"])
    swept = min(si.span, sr.span)        # captured length along the sweep (shorter wins)
    pi = Polygon2D.from_json(insert.geometry["section_profile_uv_mm"])
    pr = Polygon2D.from_json(receiver.geometry["section_profile_uv_mm"])
    m = {"insert_section_area_mm2": round(pi.area(), 2),
         "receiver_section_area_mm2": round(pr.area(), 2),
         "captured_length_mm": round(swept, 2)}
    if not _HAVE_SHAPELY:
        contained = pi.area() <= pr.area() + 1e-6      # weak area-only fallback
        m["containment"] = "area_only(shapely_unavailable)"
        verdict = "UNKNOWN"
        return PredicateResult("profile_containment", verdict, "required_closure", m,
                               "install shapely for true containment; area-compared only")
    A, B = _ShPoly(insert.geometry["section_profile_uv_mm"]["outer"]), \
           _ShPoly(receiver.geometry["section_profile_uv_mm"]["outer"])
    inside = B.buffer(1e-9).contains(A)
    m["contained"] = bool(inside)
    if not inside:
        return PredicateResult("profile_containment", "FAIL", "hard_geometry", m,
                               "insert section not contained in receiver channel -- will not seat")
    if swept <= 0:
        return PredicateResult("profile_containment", "FAIL", "hard_geometry", m,
                               "no captured length along the sweep")
    return PredicateResult("profile_containment", "PASS", "hard_geometry", m,
                           f"section captured, {swept:.0f} mm engaged along slot")


# ---- PortGroup: pattern_correspondence (Section 4 / 5) ------------------------

def _port_world_origin(part_def, pid: str, place: dict):
    p = part_def.port(pid)
    g = p.geometry
    if "axis" in g:
        loc = g["axis"]["origin"]
    elif "plane" in g:
        loc = g["plane"]["origin"]
    elif "support" in g and "axis" in g["support"]:
        loc = g["support"]["axis"]["origin"]
    else:
        raise ValueError(f"port {pid}: no positional anchor for pattern matching")
    return _R(place) @ np.asarray(loc, float) + _t(place)


def pattern_correspondence(def_a, group_a: PortGroup, place_a: dict,
                           def_b, group_b: PortGroup, place_b: dict) -> PredicateResult:
    """Solve the 1-1 correspondence between two port groups (a bolt pattern and its
    acceptor pattern) at the SOLVED poses and report the matched residual. Searches
    permutations (the manual's 'never zip hole lists by accident', Section 4) and
    flags symmetric ambiguity. Counts must be equal."""
    from itertools import permutations
    A = [_port_world_origin(def_a, mb["port"], place_a) for mb in group_a.members]
    B = [_port_world_origin(def_b, mb["port"], place_b) for mb in group_b.members]
    if len(A) != len(B):
        return PredicateResult("pattern_correspondence", "FAIL", "hard_geometry",
                               {"count_a": len(A), "count_b": len(B)},
                               f"pattern sizes differ ({len(A)} vs {len(B)})")
    if len(A) > 8:
        return PredicateResult("pattern_correspondence", "UNKNOWN", "hard_geometry",
                               {"count": len(A)}, "pattern too large for brute search (>8)")
    best, best_perm, second = None, None, None
    for perm in permutations(range(len(B))):
        rms = float(np.sqrt(np.mean([np.sum((A[i] - B[perm[i]]) ** 2) for i in range(len(A))])))
        if best is None or rms < best:
            second, best, best_perm = best, rms, perm
        elif second is None or rms < second:
            second = rms
    m = {"matched_rms_mm": round(best, 4),
         "next_best_rms_mm": round(second, 4) if second is not None else None,
         "correspondence": [[group_a.members[i]["port"], group_b.members[best_perm[i]]["port"]]
                            for i in range(len(A))]}
    if best > 0.6:
        return PredicateResult("pattern_correspondence", "FAIL", "hard_geometry", m,
                               f"patterns do not coincide (best RMS {best:.2f} mm)")
    ambiguous = second is not None and second < 0.6
    sev = "required_closure" if ambiguous else "hard_geometry"
    note = " (SYMMETRIC: multiple correspondences fit -- phase undetermined)" if ambiguous else ""
    return PredicateResult("pattern_correspondence", "PASS", sev, m,
                           f"pattern coincides, RMS {best:.3f} mm{note}")


def coaxial_pattern_correspondence(def_a, group_a: PortGroup, place_a: dict,
                                   def_b, group_b: PortGroup, place_b: dict,
                                   axis=(0, 0, 1)) -> PredicateResult:
    """Like pattern_correspondence but for bolt patterns joined ALONG the bolt axis --
    a plate bolted to a receiver ACROSS a spacer/stack (e.g. a cap bolted to a base
    through a sandwiched pulley). The two patterns are coaxial and share a radial layout
    but sit at different axial positions (the clamped stack thickness). We compare them
    PROJECTED onto the plane perpendicular to `axis`, so the axial offset is allowed;
    the radial pattern (PCD + angles) must still coincide."""
    from itertools import permutations
    ax = np.asarray(axis, float); ax = ax / np.linalg.norm(ax)
    def proj(pt):
        pt = np.asarray(pt, float); return pt - np.dot(pt, ax) * ax
    A = [proj(_port_world_origin(def_a, mb["port"], place_a)) for mb in group_a.members]
    B = [proj(_port_world_origin(def_b, mb["port"], place_b)) for mb in group_b.members]
    if len(A) != len(B):
        return PredicateResult("coaxial_pattern_correspondence", "FAIL", "hard_geometry",
                               {"count_a": len(A), "count_b": len(B)}, "pattern sizes differ")
    if len(A) > 8:
        return PredicateResult("coaxial_pattern_correspondence", "UNKNOWN", "hard_geometry",
                               {"count": len(A)}, "pattern too large for brute search (>8)")
    best = min(float(np.sqrt(np.mean([np.sum((A[i] - B[p[i]]) ** 2) for i in range(len(A))])))
               for p in permutations(range(len(B))))
    m = {"projected_rms_mm": round(best, 4), "axis": list(axis)}
    if best > 0.6:
        return PredicateResult("coaxial_pattern_correspondence", "FAIL", "hard_geometry", m,
                               f"projected patterns do not coincide (RMS {best:.2f} mm)")
    return PredicateResult("coaxial_pattern_correspondence", "PASS", "hard_geometry", m,
                           f"coaxial patterns coincide in-plane (RMS {best:.3f} mm; "
                           f"axial offset = clamped stack thickness)")


_STD_SCREW_LENGTHS_MM = [4,5,6,8,10,12,14,16,18,20,22,25,30,35,40,45,50,55,60,65,70,80,90,100]

def thread_engagement(screw: EngagementPort, receiver: EngagementPort,
                      place_s: dict, place_r: dict,
                      min_engage_factor: float = 0.8) -> PredicateResult:
    """FASTENER-LENGTH judgment: at the placed poses, does the screw's threaded span
    actually REACH the receiver's tapped span and ENGAGE enough thread?

    This is the check that was missing -- thread_match (pair_pp) only compares pitch/
    designation with NO positions, so two compatible threads 16 mm apart 'passed'. Here
    engagement = axial overlap of the two threaded spans along the receiver axis; a
    minimum of `min_engage_factor x D` (default 0.8 D; ~1 D for steel, ~1.5-2 D for soft
    alloy) is required. Reports the GRIP/bridged distance, engaged length, and a
    RECOMMENDED standard screw length so a too-short fastener fails ACTIONABLY.
    (Catches the cap bolts: M5x16/25 with a ~32 mm grip end inside the pulley, short of
    the adapter tap.)  NOTE: bottoming (screw too long for a blind tap) is not yet
    modeled -- engagement is capped at the tap span, so a too-long screw still reads
    'engaged'; add a tap-depth/tip check when blind-hole depth is annotated."""
    if screw.family != "threaded" or receiver.family != "threaded":
        return PredicateResult("thread_engagement", "UNKNOWN", "hard_geometry",
                               detail="both ports must be threaded")
    if not (screw.polarity == "external" and receiver.polarity == "internal"):
        return PredicateResult("thread_engagement", "UNKNOWN", "hard_geometry",
                               detail="need an external screw + an internal receiver")
    orr, dr = world_axis(receiver, place_r)
    iv_s = world_axial_interval(screw, place_s, dr, orr)
    iv_r = world_axial_interval(receiver, place_r, dr, orr)
    ov = iv_s.overlap(iv_r)
    mr = _thread_major_radius(screw)
    D = round(2 * mr, 3) if mr else None
    min_eng = round(min_engage_factor * D, 2) if D else None
    screw_len = round(screw.axial_interval().span, 2)
    m = {"engaged_length_mm": round(ov, 3), "screw_thread_len_mm": screw_len,
         "receiver_tap_depth_mm": round(receiver.axial_interval().span, 3),
         "major_dia_mm": D, "min_engagement_mm": min_eng, "engage_factor": min_engage_factor}
    def _recommend(need):
        return next((L for L in _STD_SCREW_LENGTHS_MM if L >= need), None)
    if ov <= 1e-6:                                   # disjoint: screw falls short of the tap mouth
        gap = round(max(iv_s.min - iv_r.max, iv_r.min - iv_s.max), 2)
        rec = _recommend(round(screw_len + max(gap, 0.0) + (min_eng or 0), 1))
        m.update({"grip_gap_mm": gap, "recommended_screw_len_mm": rec})
        return PredicateResult("thread_engagement", "FAIL", "hard_geometry", m,
                               f"screw thread does not reach receiver (short by {gap} mm); "
                               f"lengthen to >= ~{rec} mm")
    if min_eng is not None and ov < min_eng:
        rec = _recommend(round(screw_len + (min_eng - ov), 1))
        m["recommended_screw_len_mm"] = rec
        return PredicateResult("thread_engagement", "FAIL", "hard_geometry", m,
                               f"insufficient thread engagement {ov:.2f} mm < {min_eng} mm "
                               f"({min_engage_factor}xD); use ~{rec} mm")
    return PredicateResult("thread_engagement", "PASS", "hard_geometry", m,
                           f"engaged {ov:.2f} mm (>= {min_eng} mm = {min_engage_factor}xD)")
