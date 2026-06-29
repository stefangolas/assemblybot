"""Build the validated canonical candidate for projects/two_stage_rotary_table."""
from __future__ import annotations

import json
import math
from pathlib import Path

import cadquery as cq
from cadquery import exporters
import numpy as np
import trimesh

from assembly.verify_canonical import embed_verification
from ontology.ports import EngagementPort, PortGroup
from ontology.schema_v2 import EvidenceRecord, PartDefinition
from ontology.templates import TEMPLATES

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT / "projects" / "two_stage_rotary_table"
OUT = PROJECT / "out"
ASSETS = OUT / "assets"
LIB = ROOT / "library_v2"

I = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
FLIP_Z = [[1, 0, 0], [0, -1, 0], [0, 0, -1]]
Z_TO_X = [[0, 0, 1], [0, 1, 0], [-1, 0, 0]]
Z_TO_Y = [[1, 0, 0], [0, 0, 1], [0, -1, 0]]


def mm(v: float) -> float:
    return float(v) / 1000.0


def circle_points(radius: float, n: int, start_deg: float = 0.0) -> list[tuple[float, float]]:
    return [
        (
            radius * math.cos(math.radians(start_deg + 360.0 * k / n)),
            radius * math.sin(math.radians(start_deg + 360.0 * k / n)),
        )
        for k in range(n)
    ]


def circle_poly(radius: float, n: int = 48) -> list[list[float]]:
    return [[radius * math.cos(2 * math.pi * k / n), radius * math.sin(2 * math.pi * k / n)] for k in range(n)]


def rect_poly(x: float, y: float) -> list[list[float]]:
    return [[-x / 2, -y / 2], [x / 2, -y / 2], [x / 2, y / 2], [-x / 2, y / 2]]


def export_trimesh(mesh: trimesh.Trimesh | trimesh.Scene, name: str) -> str:
    ASSETS.mkdir(parents=True, exist_ok=True)
    path = ASSETS / f"{name}.glb"
    mesh.export(path)
    return f"/two_stage_rotary_table/out/assets/{name}.glb"


def cq_to_glb(obj: cq.Workplane, name: str) -> str:
    ASSETS.mkdir(parents=True, exist_ok=True)
    stl = ASSETS / f"{name}.stl"
    glb = ASSETS / f"{name}.glb"
    exporters.export(obj, str(stl))
    mesh = trimesh.load(stl, force="mesh")
    mesh.apply_scale(0.001)
    mesh.export(glb)
    return f"/two_stage_rotary_table/out/assets/{name}.glb"


def box_mesh(x: float, y: float, z: float) -> trimesh.Trimesh:
    return trimesh.creation.box(extents=(mm(x), mm(y), mm(z)))


def cyl_mesh(radius: float, height: float, sections: int = 96) -> trimesh.Trimesh:
    return trimesh.creation.cylinder(radius=mm(radius), height=mm(height), sections=sections)


def socket_screw_mesh(thread_radius: float, length: float, head_radius: float, head_height: float) -> trimesh.Scene:
    scene = trimesh.Scene()
    thread = cyl_mesh(thread_radius, length, 32)
    thread.apply_translation([0, 0, -mm(length / 2.0)])
    head = cyl_mesh(head_radius, head_height, 48)
    head.apply_translation([0, 0, mm(head_height / 2.0)])
    scene.add_geometry(thread)
    scene.add_geometry(head)
    return scene


def annular_cylinder(outer_radius: float, inner_radius: float, height: float, sections: int = 128) -> trimesh.Trimesh:
    verts: list[list[float]] = []
    faces: list[list[int]] = []
    z0, z1 = -mm(height) / 2.0, mm(height) / 2.0
    ro, ri = mm(outer_radius), mm(inner_radius)
    for z in (z0, z1):
        for r in (ro, ri):
            for k in range(sections):
                a = 2.0 * math.pi * k / sections
                verts.append([r * math.cos(a), r * math.sin(a), z])

    def idx(layer: int, ring: int, k: int) -> int:
        return layer * (2 * sections) + ring * sections + (k % sections)

    for k in range(sections):
        n = k + 1
        faces.extend([
            [idx(0, 0, k), idx(0, 0, n), idx(1, 0, n)], [idx(0, 0, k), idx(1, 0, n), idx(1, 0, k)],
            [idx(0, 1, n), idx(0, 1, k), idx(1, 1, k)], [idx(0, 1, n), idx(1, 1, k), idx(1, 1, n)],
            [idx(0, 0, n), idx(0, 0, k), idx(0, 1, k)], [idx(0, 0, n), idx(0, 1, k), idx(0, 1, n)],
            [idx(1, 0, k), idx(1, 0, n), idx(1, 1, n)], [idx(1, 0, k), idx(1, 1, n), idx(1, 1, k)],
        ])
    return trimesh.Trimesh(vertices=np.asarray(verts), faces=np.asarray(faces), process=True)


def pulley_visual(outer_radius: float, bore_radius: float, width: float, name: str) -> str:
    scene = trimesh.Scene()
    pulley = annular_cylinder(outer_radius, bore_radius, width)
    hub = annular_cylinder(max(bore_radius + 7.0, outer_radius * 0.45), bore_radius, width + 10.0, 96)
    screw = trimesh.creation.cylinder(radius=mm(2.0), height=mm(outer_radius * 0.65), sections=24)
    screw.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2.0, [0, 1, 0]))
    screw.apply_translation([mm(bore_radius + outer_radius * 0.28), 0, 0])
    scene.add_geometry(pulley)
    scene.add_geometry(hub)
    scene.add_geometry(screw)
    return export_trimesh(scene, name)


def motor_mesh() -> trimesh.Scene:
    scene = trimesh.Scene()
    body = box_mesh(60, 60, 100)
    body.apply_translation([0, 0, mm(-50)])
    flange = box_mesh(70, 70, 8)
    flange.apply_translation([0, 0, mm(4)])
    shaft = cyl_mesh(7, 95, 48)
    shaft.apply_translation([0, 0, mm(27.5)])
    scene.add_geometry(body)
    scene.add_geometry(flange)
    scene.add_geometry(shaft)
    return scene


def tslot_rail_x(length: float, name: str) -> str:
    rail = cq.Workplane("XY").box(length, 40, 80)
    # Six visible 8 mm slot mouths: one on each 40 mm face and two on each 80 mm face.
    for z in (-40, 40):
        rail = rail.cut(cq.Workplane("XY").box(length + 2, 8, 14).translate((0, 0, z)))
    for y in (-20, 20):
        for z in (-20, 20):
            rail = rail.cut(cq.Workplane("XY").box(length + 2, 14, 8).translate((0, y, z)))
    return cq_to_glb(rail, name)


def tslot_rail_y(length: float, name: str) -> str:
    rail = cq.Workplane("XY").box(40, length, 80)
    for z in (-40, 40):
        rail = rail.cut(cq.Workplane("XY").box(8, length + 2, 14).translate((0, 0, z)))
    for x in (-20, 20):
        for z in (-20, 20):
            rail = rail.cut(cq.Workplane("XY").box(14, length + 2, 8).translate((x, 0, z)))
    return cq_to_glb(rail, name)


def tslot_column_z(length: float, name: str) -> str:
    rail = cq.Workplane("XY").box(40, 80, length)
    for x in (-20, 20):
        rail = rail.cut(cq.Workplane("XY").box(14, 8, length + 2).translate((x, 0, 0)))
    for y in (-40, 40):
        for x in (-10, 10):
            rail = rail.cut(cq.Workplane("XY").box(8, 14, length + 2).translate((x, y, 0)))
    return cq_to_glb(rail, name)


def carriage_plate_visual(name: str) -> str:
    plate = cq.Workplane("XY").box(120, 120, 12)
    plate = plate.cut(cq.Workplane("XY").workplane(offset=6).circle(34).extrude(-12))
    return cq_to_glb(plate, name)


def belt_mesh(c1: tuple[float, float], r1: float, c2: tuple[float, float], r2: float, z: float, width: float) -> trimesh.Trimesh:
    c1v = np.asarray(c1, dtype=float)
    c2v = np.asarray(c2, dtype=float)
    v = c2v - c1v
    d = float(np.linalg.norm(v))
    phi = math.atan2(v[1], v[0])
    gamma = math.asin((r1 - r2) / d)
    alpha = math.pi / 2.0 - gamma
    pts: list[tuple[float, float]] = []
    n = 72
    for k in range(n + 1):
        a = (phi + alpha) + (2.0 * math.pi - 2.0 * alpha) * k / n
        pts.append((c1[0] + r1 * math.cos(a), c1[1] + r1 * math.sin(a)))
    for k in range(n + 1):
        a = (phi - alpha) + (2.0 * alpha) * k / n
        pts.append((c2[0] + r2 * math.cos(a), c2[1] + r2 * math.sin(a)))
    verts: list[list[float]] = []
    faces: list[list[int]] = []
    for x, y in pts:
        radial = np.asarray([x, y], dtype=float)
        nearest = c1v if np.linalg.norm(radial - c1v) < np.linalg.norm(radial - c2v) else c2v
        normal = radial - nearest
        normal = normal / (np.linalg.norm(normal) or 1.0)
        for side in (-0.5, 0.5):
            xy = radial + normal * 1.5 * side
            for zz in (-0.5, 0.5):
                verts.append([mm(xy[0]), mm(xy[1]), mm(z + width * zz)])
    for k in range(len(pts)):
        n0 = (k + 1) % len(pts)
        a, b = 4 * k, 4 * n0
        faces.extend([[a, b, b + 1], [a, b + 1, a + 1], [a + 2, a + 3, b + 3], [a + 2, b + 3, b + 2],
                      [a + 1, b + 1, b + 3], [a + 1, b + 3, a + 3], [a, a + 2, b + 2], [a, b + 2, b]])
    return trimesh.Trimesh(vertices=np.asarray(verts), faces=np.asarray(faces), process=True)


def threaded_port(pid: str, x: float, y: float, z: float, designation: str, pitch: float, dia: float, depth: float) -> EngagementPort:
    return EngagementPort(pid, "threaded", "internal", {
        "axis": {"origin": [x, y, z], "direction": [0, 0, 1]},
        "axial_interval_mm": {"min": -depth, "max": 0, "unit": "mm"},
        "thread": {
            "standard": "ISO_metric", "designation": designation, "pitch_mm": pitch,
            "handedness": "right", "starts": 1, "major_diameter_mm": {"min": dia - 0.2, "max": dia}
        },
    }, semantic_aliases=["threaded_hole"], evidence_refs=["ev_threaded_holes"], annotation_status="confirmed")


def external_thread_port(pid: str, designation: str, pitch: float, dia: float, length: float) -> EngagementPort:
    return EngagementPort(pid, "threaded", "external", {
        "axis": {"origin": [0, 0, 0], "direction": [0, 0, 1]},
        "axial_interval_mm": {"min": -length, "max": 0, "unit": "mm"},
        "thread": {
            "standard": "ISO_metric", "designation": designation, "pitch_mm": pitch,
            "handedness": "right", "starts": 1, "major_diameter_mm": {"min": dia - 0.2, "max": dia}
        },
    }, semantic_aliases=["screw_thread"], evidence_refs=["ev_geometry"], annotation_status="confirmed")


def radial_thread_port(pid: str, origin: list[float], direction: list[float],
                       designation: str, pitch: float, dia: float, depth: float) -> EngagementPort:
    return EngagementPort(pid, "threaded", "internal", {
        "axis": {"origin": origin, "direction": direction},
        "axial_interval_mm": {"min": -depth, "max": 0, "unit": "mm"},
        "thread": {
            "standard": "ISO_metric", "designation": designation, "pitch_mm": pitch,
            "handedness": "right", "starts": 1, "major_diameter_mm": {"min": dia - 0.2, "max": dia}
        },
    }, semantic_aliases=["radial_threaded_hole"], evidence_refs=["ev_geometry"], annotation_status="confirmed")


def cyl_insert_port(pid: str, radius: float, length: float) -> EngagementPort:
    return EngagementPort(pid, "cylindrical", "insert", {
        "axis": {"origin": [0, 0, -length / 2.0], "direction": [0, 0, 1]},
        "radial_interval_mm": {"min": 0, "max": radius, "unit": "mm"},
        "axial_interval_mm": {"min": 0, "max": length, "unit": "mm"},
        "material_side": "outside",
    }, semantic_aliases=["shaft_journal"], evidence_refs=["ev_geometry"], annotation_status="confirmed")


def cyl_receiver_port(pid: str, radius: float, length: float) -> EngagementPort:
    return EngagementPort(pid, "cylindrical", "receiver", {
        "axis": {"origin": [0, 0, -length / 2.0], "direction": [0, 0, 1]},
        "radial_interval_mm": {"min": radius, "max": radius, "unit": "mm"},
        "axial_interval_mm": {"min": 0, "max": length, "unit": "mm"},
        "material_side": "inside",
    }, semantic_aliases=["bore"], evidence_refs=["ev_geometry"], annotation_status="confirmed")


def clearance_port(pid: str, x: float, y: float, z0: float, z1: float, radius: float) -> EngagementPort:
    return EngagementPort(pid, "cylindrical", "receiver", {
        "axis": {"origin": [x, y, z0], "direction": [0, 0, 1]},
        "radial_interval_mm": {"min": radius, "max": radius, "unit": "mm"},
        "axial_interval_mm": {"min": 0, "max": z1 - z0, "unit": "mm"},
        "material_side": "inside",
    }, semantic_aliases=["clearance_hole"], evidence_refs=["ev_geometry"], annotation_status="confirmed")


def face_port(pid: str, z: float, normal_z: float, outer: list[list[float]], holes: list[list[list[float]]] | None = None) -> EngagementPort:
    return EngagementPort(pid, "planar", "contact", {
        "plane": {"origin": [0, 0, z], "normal": [0, 0, normal_z]},
        "boundary_uv_mm": {"outer": outer, "holes": holes or []},
        "material_side": "positive_normal" if normal_z > 0 else "negative_normal",
    }, semantic_aliases=["mounting_face"], evidence_refs=["ev_geometry"], annotation_status="confirmed")


def evidence() -> list[EvidenceRecord]:
    return [
        EvidenceRecord("ev_geometry", "custom_drawing", "released rotary-table geometry", {"target_path": "ports", "value": "dimensioned custom CAD", "unit": "mm"}, "projects/two_stage_rotary_table/requirements.md", "custom-part requirements", "cadquery"),
        EvidenceRecord("ev_threaded_holes", "custom_drawing", "released metric threaded hole callouts", {"target_path": "threaded ports", "value": "M5/M6 tapped holes", "unit": "mm"}, "projects/two_stage_rotary_table/requirements.md", "bearing/tabletop screw patterns", "cadquery"),
    ]


def save_part(pd: PartDefinition) -> None:
    (LIB / f"{pd.part_number}.json").write_text(json.dumps(pd.to_json(), indent=2), encoding="utf-8")


def cad_uri(viewer_url: str) -> str:
    prefix = "/two_stage_rotary_table/"
    if viewer_url.startswith(prefix):
        return "projects/two_stage_rotary_table/" + viewer_url[len(prefix):]
    return viewer_url.lstrip("/")


def make_parts(urls: dict[str, str]) -> dict[str, PartDefinition]:
    p105 = circle_points(52.5, 8, 22.5)
    p65 = circle_points(32.5, 8, 22.5)
    p90 = circle_points(45.0, 6, 0)

    base_outline = [[-90, -140], [310, -140], [310, 140], [-90, 140]]
    base_ports = [
        face_port("outer_ring_seat", 10, 1, rect_poly(180, 180), [circle_poly(48)]),
        face_port("bottom_face", -10, -1, base_outline, [circle_poly(48)]),
    ]
    for i, (x, y) in enumerate(p105, 1):
        base_ports.append(threaded_port(f"outer_thread_{i}", x, y, 10, "M5x0.8", 0.8, 5.0, 10))
    base = PartDefinition("AB_RT_BASEPLATE", {"catalog_family": "custom_machined", "aliases": ["400x280 MIC-6 baseplate"]},
        {"url": "custom_drawing:two_stage_rotary_table/baseplate"}, {}, {"dimensions_mm": [400, 280, 20]},
        {"gltf_uri": cad_uri(urls["baseplate"]), "units": "metre"}, ports=base_ports,
        port_groups=[PortGroup("outer_pattern", "repeated_ports", [{"port": f"outer_thread_{i}"} for i in range(1, 9)])],
        annotation_status={"overall": "confirmed"}, evidence=evidence(), provenance={"generated_by": "tools.build_two_stage_rotary_table"})
    save_part(base)

    brg_ports = [
        face_port("outer_bottom_face", 0, -1, circle_poly(60), [circle_poly(46.5)]),
        face_port("outer_top_face", 15, 1, circle_poly(60), [circle_poly(46.5)]),
        face_port("inner_top_face", 15, 1, circle_poly(38.5), [circle_poly(27.5)]),
    ]
    for i, (x, y) in enumerate(p105, 1):
        brg_ports.append(clearance_port(f"outer_through_{i}", x, y, 0, 15, 2.75))
    for i, (x, y) in enumerate(p65, 1):
        brg_ports.append(threaded_port(f"inner_thread_{i}", x, y, 15, "M5x0.8", 0.8, 5.0, 10))
    brg = PartDefinition("AB_RT_RU85_SIM", {"catalog_family": "crossed_roller_bearing", "aliases": ["THK RU85 validation geometry"]},
        {"url": "catalog_simplified:THK/RU85UUC0"}, {}, {"bore_mm": 55, "od_mm": 120, "width_mm": 15},
        {"gltf_uri": cad_uri(urls["bearing"]), "units": "metre"}, ports=brg_ports,
        port_groups=[
            PortGroup("outer_pattern", "repeated_ports", [{"port": f"outer_through_{i}"} for i in range(1, 9)]),
            PortGroup("inner_pattern", "repeated_ports", [{"port": f"inner_thread_{i}"} for i in range(1, 9)]),
        ], annotation_status={"overall": "confirmed"}, evidence=evidence(), provenance={"generated_by": "tools.build_two_stage_rotary_table"})
    save_part(brg)

    hub_ports = [
        face_port("inner_ring_seat", 0, -1, circle_poly(37.5), [circle_poly(20)]),
        face_port("tabletop_seat", 13, 1, circle_poly(54), [circle_poly(20)]),
        EngagementPort("spindle_journal", "cylindrical", "insert", {
            "axis": {"origin": [0, 0, -120], "direction": [0, 0, 1]},
            "radial_interval_mm": {"min": 0, "max": 25.0, "unit": "mm"},
            "axial_interval_mm": {"min": 0, "max": 120, "unit": "mm"},
            "material_side": "outside",
        }, semantic_aliases=["shaft_journal"], evidence_refs=["ev_geometry"], annotation_status="confirmed"),
    ]
    for i, (x, y) in enumerate(p65, 1):
        hub_ports.append(clearance_port(f"inner_clearance_{i}", x, y, 0, 13, 2.75))
    for i, (x, y) in enumerate(p90, 1):
        hub_ports.append(threaded_port(f"table_thread_{i}", x, y, 13, "M6x1.0", 1.0, 6.0, 13))
    hub = PartDefinition("AB_RT_HUB_SPINDLE", {"catalog_family": "custom_machined", "aliases": ["steel rotor hub spindle"]},
        {"url": "custom_drawing:two_stage_rotary_table/hub_spindle"}, {}, {"spindle_od_mm": 50, "through_bore_mm": 40, "spindle_length_mm": 120},
        {"gltf_uri": cad_uri(urls["hub"]), "units": "metre"}, ports=hub_ports,
        port_groups=[
            PortGroup("inner_pattern", "repeated_ports", [{"port": f"inner_clearance_{i}"} for i in range(1, 9)]),
            PortGroup("table_pattern", "repeated_ports", [{"port": f"table_thread_{i}"} for i in range(1, 7)]),
        ], annotation_status={"overall": "confirmed"}, evidence=evidence(), provenance={"generated_by": "tools.build_two_stage_rotary_table"})
    save_part(hub)

    table_ports = [
        face_port("bottom_face", 0, -1, rect_poly(200, 200), [circle_poly(21)]),
        face_port("top_face", 15, 1, rect_poly(200, 200), [circle_poly(21)]),
    ]
    for i, (x, y) in enumerate(p90, 1):
        table_ports.append(clearance_port(f"mount_clearance_{i}", x, y, 0, 15, 3.3))
    table = PartDefinition("AB_RT_TABLETOP", {"catalog_family": "custom_machined", "aliases": ["200x200 MIC-6 tabletop"]},
        {"url": "custom_drawing:two_stage_rotary_table/tabletop"}, {}, {"dimensions_mm": [200, 200, 15]},
        {"gltf_uri": cad_uri(urls["tabletop"]), "units": "metre"}, ports=table_ports,
        port_groups=[PortGroup("mount_pattern", "repeated_ports", [{"port": f"mount_clearance_{i}"} for i in range(1, 7)])],
        annotation_status={"overall": "confirmed"}, evidence=evidence(), provenance={"generated_by": "tools.build_two_stage_rotary_table"})
    save_part(table)

    return {"baseplate": base, "bearing": brg, "hub": hub, "tabletop": table}


def basic_part(part_number: str, family: str, url: str, ports: list[EngagementPort],
               params: dict | None = None, aliases: list[str] | None = None) -> PartDefinition:
    pd = PartDefinition(part_number, {"catalog_family": family, "aliases": aliases or []},
        {"url": f"generated_verified:two_stage_rotary_table/{part_number}"}, {}, params or {},
        {"gltf_uri": cad_uri(url), "units": "metre"}, ports=ports,
        annotation_status={"overall": "confirmed"}, evidence=evidence(),
        provenance={"generated_by": "tools.build_two_stage_rotary_table"})
    save_part(pd)
    return pd


def make_context_parts(urls: dict[str, str]) -> dict[str, PartDefinition]:
    m8 = PartDefinition("AB_RT_M8X30_SHCS", {"catalog_family": "socket_head_cap_screw", "aliases": ["M8x30 socket head screw"]},
        {"standard": "ISO 4762"}, {}, {"thread_designation": "M8x1.25", "nominal_length_mm": 30},
        {"gltf_uri": cad_uri(urls["m8_screw"]), "units": "metre"},
        ports=[
            external_thread_port("thread", "M8x1.25", 1.25, 8.0, 30.0),
            face_port("head_seat", 0, -1, rect_poly(13, 13)),
        ],
        annotation_status={"overall": "confirmed"}, evidence=evidence(),
        provenance={"generated_by": "tools.build_two_stage_rotary_table"})
    save_part(m8)

    carrier = basic_part("AB_RT_SPLIT_CARRIER", "custom_clamping_hub", urls["carrier"], [
        cyl_receiver_port("spindle_bore", 25.05, 22),
        cyl_insert_port("pulley_pilot", 35.0, 25),
        radial_thread_port("radial_clamp_thread", [0, 45, 0], [0, 1, 0], "M8x1.25", 1.25, 8.0, 25),
        face_port("pulley_seat", 12.5, 1, circle_poly(50), [circle_poly(25.4)]),
    ], {"bore_mm": 50.8, "pilot_mm": 70, "width_mm": 22}, ["split clamp carrier"])

    output_pulley72 = basic_part("AB_RT_OUTPUT_PULLEY_72T_5MGT_25", "timing_pulley", urls["pulley72_output"], [
        cyl_receiver_port("bore", 35.05, 25),
        face_port("mount_face", -12.5, -1, circle_poly(60), [circle_poly(35.05)]),
    ], {"teeth": 72, "pitch_mm": 5, "belt_width_mm": 25, "mount": "70 mm carrier pilot"}, ["72T output pulley"])

    counter_pulley72 = basic_part("AB_RT_COUNTER_PULLEY_72T_5MGT_25_15MM", "timing_pulley", urls["pulley72_counter"], [
        cyl_receiver_port("bore", 7.55, 25),
        radial_thread_port("radial_clamp_thread", [25, 0, 0], [1, 0, 0], "M5x0.8", 0.8, 5.0, 12),
        face_port("mount_face", -12.5, -1, circle_poly(60), [circle_poly(7.55)]),
    ], {"teeth": 72, "pitch_mm": 5, "belt_width_mm": 25, "bore_mm": 15, "mount": "clamp_or_keyed_hub"}, ["72T countershaft clamp pulley"])

    counter_pulley18 = basic_part("AB_RT_COUNTER_PULLEY_18T_5MGT_25_15MM", "timing_pulley", urls["pulley18_counter"], [
        cyl_receiver_port("bore", 7.55, 25),
        radial_thread_port("radial_clamp_thread", [17, 0, 0], [1, 0, 0], "M5x0.8", 0.8, 5.0, 12),
        face_port("mount_face", -12.5, -1, circle_poly(17), [circle_poly(7.55)]),
    ], {"teeth": 18, "pitch_mm": 5, "belt_width_mm": 25, "bore_mm": 15, "mount": "clamp_or_keyed_hub"}, ["18T countershaft clamp pulley"])

    motor_pulley18 = basic_part("AB_RT_MOTOR_PULLEY_18T_5MGT_25_14MM", "timing_pulley", urls["pulley18_motor"], [
        cyl_receiver_port("bore", 7.05, 25),
        radial_thread_port("radial_clamp_thread", [17, 0, 0], [1, 0, 0], "M5x0.8", 0.8, 5.0, 12),
        face_port("mount_face", -12.5, -1, circle_poly(17), [circle_poly(7.05)]),
    ], {"teeth": 18, "pitch_mm": 5, "belt_width_mm": 25, "bore_mm": 14, "mount": "servo clamp hub"}, ["18T motor pulley"])

    countershaft = basic_part("AB_RT_COUNTERSHAFT_15MM", "precision_shaft", urls["countershaft"], [
        cyl_insert_port("journal", 7.5, 130),
    ], {"diameter_mm": 15, "length_mm": 130}, ["15 mm countershaft"])

    bearing6202 = basic_part("AB_RT_6202_BEARING_HOLDER_SIM", "flanged_bearing_holder", urls["bearing6202"], [
        cyl_receiver_port("bearing_bore", 7.55, 11),
        face_port("mount_face", -5.5, -1, circle_poly(17.5), [circle_poly(7.55)]),
    ], {"bearing": "6202-2RS", "bore_mm": 15, "od_mm": 35, "width_mm": 11}, ["6202 bearing holder simplified"])

    carriage_plate = basic_part("AB_RT_COUNTER_CARRIAGE_PLATE", "custom_machined", urls["carriage_plate"], [
        face_port("top_face", 6, 1, rect_poly(120, 120)),
        face_port("bottom_face", -6, -1, rect_poly(120, 120)),
    ], {"dimensions_mm": [120, 120, 12]}, ["countershaft carriage plate"])

    standoff = basic_part("AB_RT_CARRIAGE_STANDOFF", "standoff", urls["standoff"], [
        face_port("top_face", 52, 1, circle_poly(5)),
        face_port("bottom_face", -52, -1, circle_poly(5)),
    ], {"diameter_mm": 10, "length_mm": 104}, ["M8 carriage standoff"])

    slider = basic_part("AB_RT_MOTOR_SLIDER", "custom_machined", urls["motor_slider"], [
        face_port("top_face", 6, 1, rect_poly(140, 140)),
        face_port("bottom_face", -6, -1, rect_poly(140, 140)),
    ], {"dimensions_mm": [140, 140, 12]}, ["motor slider plate"])

    motor_body = basic_part("AB_RT_SERVO_400W_SIM", "servo_motor", urls["motor_body"], [
        cyl_insert_port("shaft", 7.0, 95),
        face_port("flange_face", 8, 1, rect_poly(70, 70)),
    ], {"power_w": 400, "shaft_diameter_mm": 14}, ["400 W servo visual model"])

    rail_long = basic_part("AB_RT_RAIL_4080_400", "t_slot_extrusion", urls["rail_long"], [
        face_port("top_face", 40, 1, rect_poly(400, 40)),
        face_port("bottom_face", -40, -1, rect_poly(400, 40)),
    ], {"profile_mm": [40, 80], "length_mm": 400}, ["40x80 long rail"])

    rail_cross = basic_part("AB_RT_RAIL_4080_280", "t_slot_extrusion", urls["rail_cross"], [
        face_port("top_face", 40, 1, rect_poly(40, 280)),
        face_port("bottom_face", -40, -1, rect_poly(40, 280)),
    ], {"profile_mm": [40, 80], "length_mm": 280}, ["40x80 cross rail"])

    column = basic_part("AB_RT_COLUMN_4080_205", "t_slot_extrusion", urls["rail_column"], [
        face_port("top_face", 102.5, 1, rect_poly(40, 80)),
        face_port("bottom_face", -102.5, -1, rect_poly(40, 80)),
    ], {"profile_mm": [40, 80], "length_mm": 205}, ["40x80 vertical column"])

    return {
        "carrier": carrier,
        "output_pulley_72t": output_pulley72,
        "counter_pulley_72t": counter_pulley72,
        "counter_pulley_18t": counter_pulley18,
        "motor_pulley_18t": motor_pulley18,
        "countershaft": countershaft,
        "counter_bearing_top": bearing6202,
        "counter_bearing_lower": bearing6202,
        "counter_carriage_top": carriage_plate,
        "counter_carriage_lower": carriage_plate,
        "counter_standoff_1": standoff,
        "counter_standoff_2": standoff,
        "counter_standoff_3": standoff,
        "counter_standoff_4": standoff,
        "motor_slider": slider,
        "motor_body": motor_body,
        "upper_long_rail_1": rail_long,
        "upper_long_rail_2": rail_long,
        "upper_cross_rail_1": rail_cross,
        "upper_cross_rail_2": rail_cross,
        "frame_column_1": column,
        "frame_column_2": column,
        "frame_column_3": column,
        "frame_column_4": column,
    }


def make_validation_cad() -> dict[str, str]:
    p105 = circle_points(52.5, 8, 22.5)
    p65 = circle_points(32.5, 8, 22.5)
    p90 = circle_points(45.0, 6, 0)

    base = cq.Workplane("XY").box(400, 280, 20).translate((110, 0, 0))
    base = base.cut(cq.Workplane("XY").workplane(offset=10).circle(48).extrude(-20))
    for x, y in p105:
        base = base.cut(cq.Workplane("XY").workplane(offset=10).center(x, y).circle(2.1).extrude(-20))

    brg = cq.Workplane("XY").workplane(offset=0).circle(60).circle(27.5).extrude(15)
    brg = brg.faces(">Z").workplane().pushPoints(p105).circle(2.75).cutThruAll()
    brg = brg.faces(">Z").workplane().pushPoints(p65).circle(2.1).cutBlind(-10)

    spindle = cq.Workplane("XY").circle(25).extrude(-120)
    flange = cq.Workplane("XY").circle(54).extrude(13)
    hub = spindle.union(flange).faces(">Z").workplane().circle(20).cutThruAll()
    hub = hub.faces(">Z").workplane().pushPoints(p65).circle(2.75).cutThruAll()
    hub = hub.faces(">Z").workplane().pushPoints(p90).circle(2.5).cutBlind(-13)

    table = cq.Workplane("XY").circle(21).extrude(15)
    table = cq.Workplane("XY").box(200, 200, 15).translate((0, 0, 7.5)).faces(">Z").workplane().circle(21).cutThruAll()
    table = table.faces(">Z").workplane().pushPoints(p90).circle(3.3).cutThruAll()

    return {
        "baseplate": cq_to_glb(base, "validated_baseplate_400x280"),
        "bearing": cq_to_glb(brg, "validated_ru85_simplified"),
        "hub": cq_to_glb(hub, "validated_rotor_hub_spindle"),
        "tabletop": cq_to_glb(table, "validated_tabletop_200"),
    }


def make_visual_urls(core_urls: dict[str, str]) -> dict[str, str]:
    output, counter, motor = (0.0, 0.0), (103.59, 0.0), (207.18, 0.0)
    pitch = 5.0
    r18, r72 = 18 * pitch / (2.0 * math.pi), 72 * pitch / (2.0 * math.pi)
    urls = dict(core_urls)
    urls.update({
        "carrier": export_trimesh(annular_cylinder(50, 25.05, 22), "split_pulley_carrier_visual"),
        "pulley72_output": pulley_visual(60, 35.05, 25, "pulley_72t_5mgt_25_output_carrier_visual"),
        "pulley72_counter": pulley_visual(60, 7.55, 25, "pulley_72t_5mgt_25_15mm_clamp_visual"),
        "pulley18_counter": pulley_visual(17, 7.55, 25, "pulley_18t_5mgt_25_15mm_clamp_visual"),
        "pulley18_motor": pulley_visual(17, 7.05, 25, "pulley_18t_5mgt_25_14mm_motor_visual"),
        "countershaft": export_trimesh(cyl_mesh(7.5, 130, 48), "countershaft_15mm_visual"),
        "bearing6202": export_trimesh(annular_cylinder(17.5, 7.5, 11), "bearing_6202_visual"),
        "carriage_plate": export_trimesh(box_mesh(120, 120, 12), "countershaft_carriage_plate_visual"),
        "standoff": export_trimesh(cyl_mesh(5.0, 104, 32), "carriage_standoff_visual"),
        "motor_slider": export_trimesh(box_mesh(140, 140, 12), "motor_slider_plate_visual"),
        "motor_body": export_trimesh(motor_mesh(), "servo_motor_with_shaft_visual"),
        "m8_screw": export_trimesh(socket_screw_mesh(4.0, 30, 6.5, 8), "generated_iso4762_m8x30_visual"),
        "rail_long": tslot_rail_x(400, "mcmaster_4080_long_slotted_visual"),
        "rail_cross": tslot_rail_y(280, "mcmaster_4080_cross_slotted_visual"),
        "rail_column": tslot_column_z(205, "mcmaster_4080_column_slotted_visual"),
        "belt_lower": export_trimesh(belt_mesh(output, r72, counter, r18, -75, 25), "belt_lower_450_5mgt_25_visual"),
        "belt_upper": export_trimesh(belt_mesh(counter, r72, motor, r18, -35, 25), "belt_upper_450_5mgt_25_visual"),
    })
    return urls


def load_part(stem: str) -> PartDefinition:
    return PartDefinition.from_json(json.loads((LIB / f"{stem}.json").read_text(encoding="utf-8")))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)
    core_urls = make_validation_cad()
    urls = make_visual_urls(core_urls)
    lib = make_parts(core_urls)
    lib.update(make_context_parts(urls))

    asm: dict = {"_axis": [0, 0, 1]}
    render: list[dict] = []

    def add(ref: str, url_key: str, pose: tuple[float, float, float], name: str, group: str = "structural") -> None:
        asm[ref] = {"R": I, "t_mm": [float(pose[0]), float(pose[1]), float(pose[2])]}
        render.append({"ref": ref, "url": urls[url_key], "name": name, "group": group, "state": "HELD", "explode": 0})

    # Validated output stack.
    add("baseplate", "baseplate", (0, 0, 0), "MIC-6 main baseplate")
    add("bearing", "bearing", (0, 0, 10), "THK RU85 bearing validation geometry")
    add("hub", "hub", (0, 0, 25), "steel rotor hub and spindle")
    add("tabletop", "tabletop", (0, 0, 38), "200 x 200 mm tabletop")

    # Rendered drivetrain/layout context.
    counter, motor = (103.59, 0.0), (207.18, 0.0)
    add("carrier", "carrier", (0, 0, -75), "split-clamp pulley carrier", "context")
    add("output_pulley_72t", "pulley72_output", (0, 0, -75), "72T 5MGT output pulley", "context")
    add("countershaft", "countershaft", (*counter, -74), "15 mm precision countershaft", "context")
    add("counter_bearing_top", "bearing6202", (*counter, -16), "upper 6202-2RS bearing", "context")
    add("counter_bearing_lower", "bearing6202", (*counter, -132), "lower 6202-2RS bearing", "context")
    add("counter_carriage_top", "carriage_plate", (*counter, -16), "countershaft upper carriage plate", "context")
    add("counter_carriage_lower", "carriage_plate", (*counter, -132), "countershaft lower carriage plate", "context")
    for i, (dx, dy) in enumerate(((-45, -45), (-45, 45), (45, -45), (45, 45)), 1):
        add(f"counter_standoff_{i}", "standoff", (counter[0] + dx, counter[1] + dy, -74), "M8 carriage standoff", "context")
    add("counter_pulley_18t", "pulley18_counter", (*counter, -75), "18T 5MGT countershaft clamp pulley", "context")
    add("counter_pulley_72t", "pulley72_counter", (*counter, -35), "72T 5MGT countershaft clamp pulley", "context")
    add("motor_slider", "motor_slider", (*motor, -16), "motor slider plate", "context")
    add("motor_body", "motor_body", (*motor, -30), "400 W servo motor with shaft", "context")
    add("motor_pulley_18t", "pulley18_motor", (*motor, -35), "18T 5MGT motor clamp pulley", "context")
    add("belt_output_stage", "belt_lower", (0, 0, 0), "lower 450-5MGT-25 belt", "belt")
    add("belt_motor_stage", "belt_upper", (0, 0, 0), "upper 450-5MGT-25 belt", "belt")
    for i, y in enumerate((-120, 120), 1):
        add(f"upper_long_rail_{i}", "rail_long", (110, y, -50.5), "McMaster 40 x 80 long frame rail", "context")
    for i, x in enumerate((-90, 310), 1):
        add(f"upper_cross_rail_{i}", "rail_cross", (x, 0, -50.5), "McMaster 40 x 80 cross frame rail", "context")
    for i, (x, y) in enumerate(((-90, -120), (-90, 120), (310, -120), (310, 120)), 1):
        add(f"frame_column_{i}", "rail_column", (x, y, -193), "McMaster 40 x 80 vertical column", "context")

    # Real fastener instances for the validated load path.
    p105 = circle_points(52.5, 8, 22.5)
    p65 = circle_points(32.5, 8, 22.5)
    p90 = circle_points(45.0, 6, 0)
    for i, (x, y) in enumerate(p105, 1):
        ref = f"scr_outer_{i}"
        lib[ref] = load_part("ISO4762-M5x0.8-25")
        asm[ref] = {"R": I, "t_mm": [x, y, 25]}
        render.append({"ref": ref, "url": "/cad/ISO4762-M5x0.8-25.glb", "name": "M5x25 outer-ring screw", "group": "fastener", "state": "HELD"})
    for i, (x, y) in enumerate(p65, 1):
        ref = f"scr_inner_{i}"
        lib[ref] = load_part("ISO4762-M5x0.8-25")
        asm[ref] = {"R": I, "t_mm": [x, y, 38]}
        render.append({"ref": ref, "url": "/cad/ISO4762-M5x0.8-25.glb", "name": "M5x25 inner-ring screw", "group": "fastener", "state": "HELD"})
    for i, (x, y) in enumerate(p90, 1):
        ref = f"scr_table_{i}"
        lib[ref] = load_part("ISO4762-M6x1.0-30")
        asm[ref] = {"R": I, "t_mm": [x, y, 53]}
        render.append({"ref": ref, "url": "/cad/ISO4762-M6x1.0-30.glb", "name": "M6x30 tabletop screw", "group": "fastener", "state": "HELD"})

    def hidden_m8(ref: str, pose: tuple[float, float, float], R: list[list[float]] = I) -> str:
        lib[ref] = load_part("AB_RT_M8X30_SHCS")
        asm[ref] = {"R": R, "t_mm": [float(pose[0]), float(pose[1]), float(pose[2])]}
        render.append({"ref": ref, "url": urls["m8_screw"], "name": "M8 structural screw", "group": "fastener", "state": "HELD", "explode": 0})
        return ref

    def visible_m8(ref: str, pose: tuple[float, float, float], name: str, R: list[list[float]] = I) -> str:
        hidden_m8(ref, pose, R)
        for item in reversed(render):
            if item["ref"] == ref:
                item["name"] = name
                break
        return ref

    def hidden_m5(ref: str, pose: tuple[float, float, float], R: list[list[float]] = I) -> str:
        lib[ref] = load_part("ISO4762-M5x0.8-25")
        asm[ref] = {"R": R, "t_mm": [float(pose[0]), float(pose[1]), float(pose[2])]}
        render.append({"ref": ref, "url": "/cad/ISO4762-M5x0.8-25.glb", "name": "M5 structural screw", "group": "fastener", "state": "HELD", "explode": 0})
        return ref

    hidden_m8("fast_carrier_clamp", (0, 45, -75), Z_TO_Y)
    hidden_m5("fast_output_pulley", (0, 43, -62))
    hidden_m5("fast_counter_pulley_18", (counter[0] + 18, counter[1], -75), Z_TO_X)
    hidden_m5("fast_counter_pulley_72", (counter[0] + 25, counter[1], -35), Z_TO_X)
    hidden_m5("fast_motor_pulley", (motor[0] + 18, motor[1], -35), Z_TO_X)
    hidden_m8("fast_counter_top_to_base", (counter[0] - 45, counter[1] - 45, -10))
    hidden_m8("fast_motor_slider_to_base", (motor[0] - 45, motor[1] - 45, -10))
    hidden_m8("fast_motor_to_slider", (motor[0] - 25, motor[1] - 25, -22))
    for i, (dx, dy) in enumerate(((-45, -45), (-45, 45), (45, -45), (45, 45)), 1):
        visible_m8(f"fast_standoff_top_{i}", (counter[0] + dx, counter[1] + dy, -10), "M8 upper carriage-to-standoff screw")
        visible_m8(f"fast_standoff_lower_{i}", (counter[0] + dx, counter[1] + dy, -138), "M8 lower carriage-to-standoff screw", FLIP_Z)
        hidden_m8(f"fast_column_{i}", (0, 0, -90))
    for i in range(1, 3):
        hidden_m8(f"fast_rail_long_{i}", (110, -120 if i == 1 else 120, -10))
        hidden_m8(f"fast_rail_cross_{i}", (-90 if i == 1 else 310, 0, -10))
        hidden_m8(f"fast_bearing_{i}", (counter[0] + 28, counter[1] + 28, -16 if i == 1 else -132))

    placements = {ref: asm[ref] for ref in lib}
    inst = [
        TEMPLATES["bounded_bolt_pattern_seat"].bind({"plate": "bearing.outer_bottom_face", "seat": "baseplate.outer_ring_seat", "plate_group": "bearing:outer_pattern", "seat_group": "baseplate:outer_pattern"}),
        TEMPLATES["bounded_bolt_pattern_seat"].bind({"plate": "hub.inner_ring_seat", "seat": "bearing.inner_top_face", "plate_group": "hub:inner_pattern", "seat_group": "bearing:inner_pattern"}),
        TEMPLATES["bounded_bolt_pattern_seat"].bind({"plate": "tabletop.bottom_face", "seat": "hub.tabletop_seat", "plate_group": "tabletop:mount_pattern", "seat_group": "hub:table_pattern"}),
    ]
    for i in range(1, 9):
        inst.append(TEMPLATES["screw_into_threaded_receiver"].bind({"screw": f"scr_outer_{i}.thread", "receiver": f"baseplate.outer_thread_{i}", "bearing": "bearing.outer_top_face"}))
        inst.append(TEMPLATES["screw_into_threaded_receiver"].bind({"screw": f"scr_inner_{i}.thread", "receiver": f"bearing.inner_thread_{i}", "bearing": "hub.tabletop_seat"}))
    for i in range(1, 7):
        inst.append(TEMPLATES["screw_into_threaded_receiver"].bind({"screw": f"scr_table_{i}.thread", "receiver": f"hub.table_thread_{i}", "bearing": "tabletop.top_face"}))

    inst.extend([
        TEMPLATES["radial_screw_against_cylindrical_target"].bind({
            "body_bore": "carrier.spindle_bore",
            "target": "hub.spindle_journal",
            "screw": "fast_carrier_clamp.thread",
            "thread": "carrier.radial_clamp_thread",
        }),
        TEMPLATES["pilot_clamped_hub_to_carrier"].bind({
            "hub": "output_pulley_72t.bore",
            "pilot": "carrier.pulley_pilot",
            "hub_seat": "output_pulley_72t.mount_face",
            "seat": "carrier.pulley_seat",
            "clamp_fastener": "fast_output_pulley.thread",
        }),
        TEMPLATES["radial_screw_against_cylindrical_target"].bind({
            "body_bore": "counter_pulley_18t.bore",
            "target": "countershaft.journal",
            "screw": "fast_counter_pulley_18.thread",
            "thread": "counter_pulley_18t.radial_clamp_thread",
        }),
        TEMPLATES["radial_screw_against_cylindrical_target"].bind({
            "body_bore": "counter_pulley_72t.bore",
            "target": "countershaft.journal",
            "screw": "fast_counter_pulley_72.thread",
            "thread": "counter_pulley_72t.radial_clamp_thread",
        }),
        TEMPLATES["radial_screw_against_cylindrical_target"].bind({
            "body_bore": "motor_pulley_18t.bore",
            "target": "motor_body.shaft",
            "screw": "fast_motor_pulley.thread",
            "thread": "motor_pulley_18t.radial_clamp_thread",
        }),
        TEMPLATES["journal_supported_by_bearing"].bind({"journal": "countershaft.journal", "bearing": "counter_bearing_top.bearing_bore"}),
        TEMPLATES["journal_supported_by_bearing"].bind({"journal": "countershaft.journal", "bearing": "counter_bearing_lower.bearing_bore"}),
    ])

    def face_mount(mounted: str, support: str, fastener: str) -> None:
        inst.append(TEMPLATES["fastened_face_mount"].bind({
            "mounted": mounted,
            "support": support,
            "fastener": f"{fastener}.thread",
        }))

    face_mount("counter_bearing_top.mount_face", "counter_carriage_top.bottom_face", "fast_bearing_1")
    face_mount("counter_bearing_lower.mount_face", "counter_carriage_lower.bottom_face", "fast_bearing_2")
    face_mount("counter_carriage_top.top_face", "baseplate.bottom_face", "fast_counter_top_to_base")
    for i in range(1, 5):
        face_mount(f"counter_carriage_lower.top_face", f"counter_standoff_{i}.bottom_face", f"fast_standoff_lower_{i}")
        face_mount(f"counter_standoff_{i}.top_face", "counter_carriage_top.bottom_face", f"fast_standoff_top_{i}")

    face_mount("motor_body.flange_face", "motor_slider.bottom_face", "fast_motor_to_slider")
    face_mount("motor_slider.top_face", "baseplate.bottom_face", "fast_motor_slider_to_base")
    face_mount("upper_long_rail_1.top_face", "baseplate.bottom_face", "fast_rail_long_1")
    face_mount("upper_long_rail_2.top_face", "baseplate.bottom_face", "fast_rail_long_2")
    face_mount("upper_cross_rail_1.top_face", "baseplate.bottom_face", "fast_rail_cross_1")
    face_mount("upper_cross_rail_2.top_face", "baseplate.bottom_face", "fast_rail_cross_2")
    face_mount("frame_column_1.top_face", "upper_long_rail_1.bottom_face", "fast_column_1")
    face_mount("frame_column_2.top_face", "upper_long_rail_2.bottom_face", "fast_column_2")
    face_mount("frame_column_3.top_face", "upper_long_rail_1.bottom_face", "fast_column_3")
    face_mount("frame_column_4.top_face", "upper_long_rail_2.bottom_face", "fast_column_4")

    asm["_render"] = render
    asm["_dofs"] = [{"id": "output_axis", "type": "revolute", "axis": [0, 0, 1], "center": [0, 0, 0], "range": [-180, 180], "moving": ["hub", "tabletop"]}]
    embed_verification(asm, lib=lib, instances=inst, ground=["baseplate"], placements=placements,
                       non_structural={"belt_output_stage", "belt_motor_stage"})

    out_path = OUT / "two_stage_rotary_table_assembly.json"
    out_path.write_text(json.dumps(asm, indent=2), encoding="utf-8")

    meta_path = PROJECT / "project.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["canonical_assembly"] = "out/two_stage_rotary_table_assembly.json"
    meta["status"] = "blocked"
    meta["verification"] = (
        "FAIL: primitive fastener/contact ontology refactor is incomplete; remaining "
        "face mounts and visual clearances require explicit screw/hole/thread ports"
    )
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    state_path = PROJECT / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["stage"] = "assembly"
    state["status"] = "blocked: remaining face mounts require primitive screw/hole/thread authoring"
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    print(f"wrote {out_path}")
    print(f"wrote {len(render)} render parts, {len(lib)} verified parts, {len(inst)} attachment instances")


if __name__ == "__main__":
    main()
