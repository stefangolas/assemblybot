"""Mesh-level CAD fidelity check (the phantom-hole gate).

Every declared internal void -- a `cylindrical` receiver or an `internal` `threaded`
port -- must PHYSICALLY exist in the part's mesh at the declared location, axial span,
AND diameter. This audits the exported deliverable (the glTF mesh), not the build script,
so it works for custom-generated parts AND catalog-fetched parts alike.

Why sectioning, not raycasting: every rung-3 custom mesh is non-watertight (cascadio glTF),
where trimesh ray inside/outside tests are unreliable, and a single axial ray cannot see a
missing/undersized counterbore (the central ray passes through the clearance hole cleanly).
A planar SECTION perpendicular to the port axis returns the actual hole loop, so we read the
real radius -- bounding BOTH undersize and oversize -- and by sectioning at the port's own
declared span we catch a counterbore that is missing, too small, or cut on the WRONG side
(at the counterbore's mid-depth there is only the narrow clearance Ø, not the wide bore).

Threads are modeled at their tap-drill (minor) representation in CAD (helices omitted -- an
explicit reconciliation policy), so an internal threaded port's expected void radius is the
tap-drill radius, not the nominal major radius.

Custom parts BLOCK on a phantom; catalog parts WARN (their CAD may legitimately smooth
features per a reconciliation policy) -- but an unexplained catalog miss is still surfaced.
"""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parent.parent

# tap-drill diameters for the modeled (minor) thread representation -- mirror build_rotary_custom.py
TAP_DRILL_MM = {"M3": 2.50, "M4": 3.30, "M5": 4.20, "M6": 5.00, "M8": 6.80}


# --------------------------------------------------------------------------- input adapter
def _as_dict(part_def) -> dict:
    """Accept a v2 PartDefinition object (has .to_json) or a raw dict."""
    if hasattr(part_def, "to_json"):
        return part_def.to_json()
    return part_def


# --------------------------------------------------------------------------- geometry helpers
def _unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


def _dist_point_to_line(p, o, d):
    """Perpendicular distance from point p to the line through o with unit direction d."""
    w = np.asarray(p, float) - np.asarray(o, float)
    return float(np.linalg.norm(w - np.dot(w, d) * d))


def _thread_root(designation: str):
    if not designation:
        return None
    return designation.split("x")[0].strip().upper()


def _expected_radius_mm(port: dict):
    """The void radius we expect to see in the mesh for this port (mm), or None if N/A."""
    fam = port.get("family")
    geom = port.get("geometry", {})
    if fam == "cylindrical" and port.get("polarity") == "receiver":
        ri = geom.get("radial_interval_mm", {})
        if "max" in ri:
            return float(ri["max"])
    elif fam == "threaded" and port.get("polarity") == "internal":
        root = _thread_root((geom.get("thread") or {}).get("designation", ""))
        if root in TAP_DRILL_MM:
            return TAP_DRILL_MM[root] / 2.0
    return None


def _axis(port: dict):
    a = port["geometry"]["axis"]
    return np.asarray(a["origin"], float), _unit(a["direction"])


def _span(port: dict):
    s = port["geometry"]["axial_interval_mm"]
    return float(s["min"]), float(s["max"])


# --------------------------------------------------------------------------- mesh loading
def load_mesh_mm(part_def: dict):
    """Load the part's glTF and return it in MILLIMETRES in the part-local frame.

    glTF is metres at the boundary -> scale 1000. The drawing_to_cad transform is applied
    so ports authored in the drawing frame are checked against the right place in the CAD.
    """
    uri = (part_def.get("cad") or {}).get("gltf_uri")
    if not uri:
        return None
    p = (ROOT / uri.lstrip("/")).resolve()
    if not p.exists():
        return None
    s = trimesh.load(p, force="scene")
    geoms = list(s.geometry.values())
    if not geoms:
        return None
    m = trimesh.util.concatenate(geoms)
    m.apply_scale(1000.0)  # metres -> mm

    d2c = (part_def.get("part_frame") or {}).get("drawing_to_cad") or {}
    rot = d2c.get("rotation", "identity")
    if isinstance(rot, list) and len(rot) == 3:  # explicit 3x3 matrix only
        T = np.eye(4)
        T[:3, :3] = np.asarray(rot, float)
        T[:3, 3] = np.asarray(d2c.get("translation", [0, 0, 0]), float)
        m.apply_transform(np.linalg.inv(T))  # CAD frame -> drawing frame (where ports live)
    return m


# --------------------------------------------------------------------------- the section probe
def _radius_at(mesh, origin, direction, t, center_tol):
    """Section perpendicular to the axis at origin+direction*t; return measured radius of the
    loop nearest the axis, or None if no loop is near the axis there (solid metal)."""
    plane_o = np.asarray(origin, float) + direction * t
    sec = mesh.section(plane_origin=plane_o, plane_normal=direction)
    if sec is None:
        return None
    try:
        p2d, to3d = sec.to_2D() if hasattr(sec, "to_2D") else sec.to_planar()
    except Exception:
        return None
    best = None
    for loop in p2d.discrete:                       # each loop: (N,2)
        pts3d = trimesh.transformations.transform_points(
            np.column_stack([loop, np.zeros(len(loop))]), to3d)
        c = pts3d.mean(axis=0)
        off = _dist_point_to_line(c, origin, direction)
        if off > center_tol:
            continue
        r = float(np.linalg.norm(pts3d - c, axis=1).mean())
        if best is None or off < best[1]:
            best = (r, off)
    return None if best is None else best[0]


def verify_port(mesh, port: dict, *, rtol=0.15, rfloor=0.4):
    """Check one internal-void port against the mesh. Returns a result dict, or None if the
    port is not an internal void (faces / external threads / etc. are skipped)."""
    exp_r = _expected_radius_mm(port)
    if exp_r is None:
        return None
    origin, direction = _axis(port)
    s0, s1 = _span(port)
    L = s1 - s0
    if L <= 0:
        return None
    ts = [s0 + f * L for f in (0.25, 0.5, 0.75)]     # sample inside the span, avoid end faces
    center_tol = max(1.5, 0.5 * exp_r)
    tol = max(rfloor, rtol * exp_r)

    measured, missing_at = [], []
    for t in ts:
        r = _radius_at(mesh, origin, direction, t, center_tol)
        if r is not None:
            measured.append(r)
        else:
            missing_at.append(round(t, 2))

    res = {"id": port["id"], "family": port["family"], "expected_r_mm": round(exp_r, 3),
           "span_mm": [s0, s1], "n_samples": len(ts)}
    if len(measured) < len(ts):
        res["status"] = "PHANTOM"
        res["measured_r_mm"] = round(float(np.median(measured)), 3) if measured else None
        res["detail"] = f"void absent at depth(s) {missing_at} mm along axis from origin"
        return res
    rmed = float(np.median(measured))
    res["measured_r_mm"] = round(rmed, 3)
    if rmed < exp_r - tol:
        res["status"] = "UNDERSIZE"
        res["detail"] = f"measured O{2*rmed:.2f} < expected O{2*exp_r:.2f} (tol +-{2*tol:.2f})"
    elif rmed > exp_r + tol:
        res["status"] = "OVERSIZE"
        res["detail"] = f"measured O{2*rmed:.2f} > expected O{2*exp_r:.2f} (tol +-{2*tol:.2f})"
    else:
        res["status"] = "OK"
    return res


# --------------------------------------------------------------------------- part-level gate
def _is_custom(part_def: dict) -> bool:
    url = ((part_def.get("source") or {}).get("url") or "")
    fam = ((part_def.get("classification") or {}).get("catalog_family") or "")
    return url.startswith("custom_drawing") or fam == "custom_machined"


def check_part(part_def) -> dict:
    """Return {part_number, custom, mesh_found, results:[...], phantom_ids:[...], ok}.
    `ok` is True when no internal-void port is PHANTOM / UNDERSIZE / OVERSIZE."""
    pd = _as_dict(part_def)
    pn = pd.get("part_number", "?")
    mesh = load_mesh_mm(pd)
    out = {"part_number": pn, "custom": _is_custom(pd),
           "mesh_found": mesh is not None, "results": [], "phantom_ids": [], "ok": True}
    if mesh is None:
        out["ok"] = False
        out["error"] = "mesh not found (cad.gltf_uri missing/absent)"
        return out
    for port in pd.get("ports", []):
        r = verify_port(mesh, port)
        if r is None:
            continue
        out["results"].append(r)
        if r["status"] != "OK":
            out["phantom_ids"].append(r["id"])
            out["ok"] = False
    return out


def check_part_file(json_path) -> dict:
    return check_part(json.loads(Path(json_path).read_text()))


# --------------------------------------------------------------------------- compat shim
def verify_mesh_holes(part_def, repo_root=None) -> list:
    """Back-compat entry point: return the list of phantom/mis-sized port IDs for one part.
    Accepts a v2 PartDefinition or a raw dict. `repo_root` is ignored (paths resolve from the
    library root); kept for signature compatibility with the original stub."""
    return check_part(part_def)["phantom_ids"]


def gate(part_defs: list, *, verbose=True):
    """Run the cad_fidelity gate over a list of part-defs (objects or dicts).
    Custom failures BLOCK (gate fails); catalog failures WARN (gate still passes).
    Returns (passed: bool, reports: list)."""
    reports, blocked, warned = [], [], []
    for pd in part_defs:
        rep = check_part(pd)
        reports.append(rep)
        if not rep["ok"]:
            (blocked if rep["custom"] else warned).append(rep)
    if verbose:
        for rep in reports:
            if rep["ok"]:
                print(f"  cad_fidelity  OK     {rep['part_number']:34s} "
                      f"({len(rep['results'])} void ports verified)")
            else:
                tag = "BLOCK " if rep["custom"] else "WARN  "
                ids = ", ".join(f"{r['id']}:{r['status']}" for r in rep["results"]
                                if r["status"] != "OK") or rep.get("error", "?")
                print(f"  cad_fidelity  {tag}{rep['part_number']:34s} {ids}")
        status = "PASS" if not blocked else "FAIL"
        extra = f" ({len(warned)} catalog warning(s))" if warned else ""
        print(f"  cad_fidelity GATE: {status}{extra}")
    return (not blocked), reports


if __name__ == "__main__":
    import sys
    files = sys.argv[1:] or [str(p) for p in sorted((ROOT / "library_v2").glob("ROTARY_*.json"))]
    defs = [json.loads(Path(f).read_text()) for f in files]
    ok, _ = gate(defs)
    sys.exit(0 if ok else 1)
