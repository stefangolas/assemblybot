import os
import json
import math
from ontology.ports import EngagementPort, PortGroup
from ontology.schema_v2 import PartDefinition, EvidenceRecord

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBV2 = os.path.join(ROOT, "library_v2")
os.makedirs(LIBV2, exist_ok=True)

PX = [1.0, 0.0, 0.0]
NX = [-1.0, 0.0, 0.0]
PY = [0.0, 1.0, 0.0]
NY = [0.0, -1.0, 0.0]
PZ = [0.0, 0.0, 1.0]
NZ = [0.0, 0.0, -1.0]

def ring_yz(r_in, r_out, n=48):
    th = [2*math.pi*k/n for k in range(n)]
    return {"outer": [[round(r_out*math.cos(t), 4), round(r_out*math.sin(t), 4)] for t in th],
            "holes": [[[round(r_in*math.cos(t), 4), round(r_in*math.sin(t), 4)] for t in th]]}

def ring_xy(r_in, r_out, n=48):
    th = [2*math.pi*k/n for k in range(n)]
    return {"outer": [[round(r_out*math.cos(t), 4), round(r_out*math.sin(t), 4)] for t in th],
            "holes": [[[round(r_in*math.cos(t), 4), round(r_in*math.sin(t), 4)] for t in th]]}

def rect(x0, x1, y0, y1):
    return {"outer": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], "holes": []}

def pcd_points(r, n=8, start=22.5):
    pts = []
    for k in range(n):
        ang = math.radians(start + (360.0 / n) * k)
        pts.append((round(r * math.cos(ang), 4), round(r * math.sin(ang), 4)))
    return pts

def save_part(part_def: PartDefinition):
    dest = os.path.join(LIBV2, f"{part_def.part_number}.json")
    with open(dest, "w") as f:
        json.dump(part_def.to_json(), f, indent=2)
    print(f"Authored {part_def.part_number} library entry -> {dest}")

# ============================================================================
# 1. RU66 bearing (RU66UUC0)
# ============================================================================
def author_ru66():
    ports = [
        EngagementPort("bore", "cylindrical", "receiver",
            {"axis": {"origin": [0.0, 0.0, 0.0], "direction": PX},
             "radial_interval_mm": {"min": 17.5, "max": 17.5, "unit": "mm"},
             "axial_interval_mm": {"min": 0.0, "max": 15.0, "unit": "mm"}, "material_side": "inside"},
            semantic_aliases=["bore_35", "pass_through"], annotation_status="confirmed"),
        EngagementPort("outer_ring_base_face", "planar", "contact",
            {"plane": {"origin": [0.0, 0.0, 0.0], "normal": NX}, "boundary_uv_mm": ring_yz(27.5, 47.5), "material_side": "positive_normal"},
            semantic_aliases=["outer_race_seat"], annotation_status="confirmed"),
        EngagementPort("outer_ring_adapter_face", "planar", "contact",
            {"plane": {"origin": [15.0, 0.0, 0.0], "normal": PX}, "boundary_uv_mm": ring_yz(27.5, 47.5), "material_side": "negative_normal"},
            semantic_aliases=["outer_race_forbidden"], annotation_status="confirmed"),
        EngagementPort("inner_ring_adapter_face", "planar", "contact",
            {"plane": {"origin": [15.0, 0.0, 0.0], "normal": PX}, "boundary_uv_mm": ring_yz(17.5, 23.5), "material_side": "negative_normal"},
            semantic_aliases=["inner_race_seat"], annotation_status="confirmed"),
        EngagementPort("inner_ring_base_face", "planar", "contact",
            {"plane": {"origin": [0.0, 0.0, 0.0], "normal": NX}, "boundary_uv_mm": ring_yz(17.5, 23.5), "material_side": "positive_normal"},
            semantic_aliases=["inner_race_forbidden"], annotation_status="confirmed")
    ]
    groups = []
    for i, (y, z) in enumerate(pcd_points(22.5, 8, 22.5), 1):
        ports.append(EngagementPort(f"inner_thread_{i}", "threaded", "internal",
            {"axis": {"origin": [15.0, y, z], "direction": NX},
             "axial_interval_mm": {"min": 0.0, "max": 15.0, "unit": "mm"},
             "thread": {"standard": "ISO_metric", "designation": "M4x0.7", "pitch_mm": 0.7, "handedness": "right", "starts": 1}},
            annotation_status="confirmed"))
    groups.append(PortGroup("inner_ring_pattern", "repeated_ports",
        members=[{"port": f"inner_thread_{i}"} for i in range(1, 9)],
        symmetry={"generators": [{"rotation_deg": 45}]}))
        
    for i, (y, z) in enumerate(pcd_points(41.5, 8, 22.5), 1):
        ports.append(EngagementPort(f"outer_through_{i}", "cylindrical", "receiver",
            {"axis": {"origin": [0.0, y, z], "direction": PX},
             "radial_interval_mm": {"min": 2.25, "max": 2.25, "unit": "mm"},
             "axial_interval_mm": {"min": 0.0, "max": 15.0, "unit": "mm"}, "material_side": "inside"},
            annotation_status="confirmed"))
    groups.append(PortGroup("outer_ring_pattern", "repeated_ports",
        members=[{"port": f"outer_through_{i}"} for i in range(1, 9)],
        symmetry={"generators": [{"rotation_deg": 45}]}))

    pd = PartDefinition(
        part_number="RU66UUC0",
        classification={"catalog_family": "crossed_roller_ring", "broader_families": ["precision_bearing"]},
        source={"url": "misumi:RU66UUC0", "retrieved_at": "2026-06-25", "brand": "THK"},
        normalized_parameters={"bore_mm": 35, "od_mm": 95, "width_mm": 15, "inner_PCD_mm": 45, "outer_PCD_mm": 83, "inner_thread": "M4", "outer_hole_dia_mm": 4.5},
        cad={"gltf_uri": "cad/RU66UUC0.glb", "units": "metre"},
        part_frame={"units": "millimetre", "drawing_to_cad": {"scale": 1.0, "rotation": "identity", "translation": [0,0,0]}},
        ports=ports,
        port_groups=groups
    )
    save_part(pd)

# ============================================================================
# 2. NEMA 17 Motor (iCL42-06)
# ============================================================================
def author_nema17():
    nema17_bnd = {"outer": [[-21.0, -21.0], [21.0, -21.0], [21.0, 21.0], [-21.0, 21.0]], "holes": []}
    ports = [
        EngagementPort("shaft", "cylindrical", "insert",
            {"axis": {"origin": [0.0, 0.0, 42.0], "direction": PZ},
             "radial_interval_mm": {"min": 2.5, "max": 2.5, "unit": "mm"},
             "axial_interval_mm": {"min": 0.0, "max": 24.0, "unit": "mm"}, "material_side": "outside"},
            semantic_aliases=["motor_shaft"], annotation_status="confirmed"),
        EngagementPort("pilot", "cylindrical", "insert",
            {"axis": {"origin": [0.0, 0.0, 40.0], "direction": PZ},
             "radial_interval_mm": {"min": 11.0, "max": 11.0, "unit": "mm"},
             "axial_interval_mm": {"min": 0.0, "max": 2.0, "unit": "mm"}, "material_side": "outside"},
            semantic_aliases=["locating_pilot"], annotation_status="confirmed"),
        EngagementPort("front_face", "planar", "contact",
            {"plane": {"origin": [0.0, 0.0, 40.0], "normal": PZ}, "boundary_uv_mm": nema17_bnd, "material_side": "negative_normal"},
            semantic_aliases=["mounting_face"], annotation_status="confirmed")
    ]
    groups = []
    i = 1
    for x in [-15.5, 15.5]:
        for y in [-15.5, 15.5]:
            ports.append(EngagementPort(f"mount_thread_{i}", "threaded", "internal",
                {"axis": {"origin": [x, y, 40.0], "direction": NZ},
                 "axial_interval_mm": {"min": 0.0, "max": 4.5, "unit": "mm"},
                 "thread": {"standard": "ISO_metric", "designation": "M3x0.5", "pitch_mm": 0.5, "handedness": "right", "starts": 1}},
                annotation_status="confirmed"))
            i += 1
    groups.append(PortGroup("mount_pattern", "repeated_ports",
        members=[{"port": f"mount_thread_{k}"} for k in range(1, 5)]))
        
    pd = PartDefinition(
        part_number="iCL42-06",
        classification={"catalog_family": "stepper_motor", "broader_families": ["actuator"]},
        source={"url": "stepperonline:iCL42-06", "retrieved_at": "2026-06-25", "brand": "StepperOnline"},
        normalized_parameters={"frame_size_nema": 17, "shaft_diameter_mm": 5.0, "pilot_diameter_mm": 22.0, "mount_pattern_span_mm": 31.0, "mount_thread": "M3"},
        cad={"gltf_uri": "cad/iCL42-06.glb", "units": "metre"},
        part_frame={"units": "millimetre", "drawing_to_cad": {"scale": 1.0, "rotation": "identity", "translation": [0,0,0]}},
        ports=ports,
        port_groups=groups
    )
    save_part(pd)

# ============================================================================
# 3. NEMA 23 Motor (iCL57-23)
# ============================================================================
def author_nema23():
    nema23_bnd = {"outer": [[-28.5, -28.5], [28.5, -28.5], [28.5, 28.5], [-28.5, 28.5]], "holes": []}
    ports = [
        EngagementPort("shaft", "cylindrical", "insert",
            {"axis": {"origin": [0.0, 0.0, 81.6], "direction": PZ},
             "radial_interval_mm": {"min": 4.0, "max": 4.0, "unit": "mm"},
             "axial_interval_mm": {"min": 0.0, "max": 21.0, "unit": "mm"}, "material_side": "outside"},
            semantic_aliases=["motor_shaft"], annotation_status="confirmed"),
        EngagementPort("pilot", "cylindrical", "insert",
            {"axis": {"origin": [0.0, 0.0, 80.0], "direction": PZ},
             "radial_interval_mm": {"min": 19.05, "max": 19.05, "unit": "mm"},
             "axial_interval_mm": {"min": 0.0, "max": 1.6, "unit": "mm"}, "material_side": "outside"},
            semantic_aliases=["locating_pilot"], annotation_status="confirmed"),
        EngagementPort("front_face", "planar", "contact",
            {"plane": {"origin": [0.0, 0.0, 80.0], "normal": PZ}, "boundary_uv_mm": nema23_bnd, "material_side": "negative_normal"},
            semantic_aliases=["mounting_face"], annotation_status="confirmed"),
        EngagementPort("back_face", "planar", "contact",
            {"plane": {"origin": [0.0, 0.0, 0.0], "normal": NZ}, "boundary_uv_mm": nema23_bnd, "material_side": "positive_normal"},
            semantic_aliases=["motor_rear_screw_head_face"], annotation_status="confirmed")
    ]
    groups = []
    i = 1
    for x in [-23.57, 23.57]:
        for y in [-23.57, 23.57]:
            ports.append(EngagementPort(f"mount_through_{i}", "cylindrical", "receiver",
                {"axis": {"origin": [x, y, 80.0], "direction": NZ},
                 "radial_interval_mm": {"min": 2.5, "max": 2.5, "unit": "mm"},
                 "axial_interval_mm": {"min": 0.0, "max": 80.0, "unit": "mm"}, "material_side": "inside"},
                annotation_status="confirmed"))
            i += 1
    groups.append(PortGroup("mount_pattern", "repeated_ports",
        members=[{"port": f"mount_through_{k}"} for k in range(1, 5)]))

    pd = PartDefinition(
        part_number="iCL57-23",
        classification={"catalog_family": "stepper_motor", "broader_families": ["actuator"]},
        source={"url": "stepperonline:iCL57-23", "retrieved_at": "2026-06-25", "brand": "StepperOnline"},
        normalized_parameters={"frame_size_nema": 23, "shaft_diameter_mm": 8.0, "pilot_diameter_mm": 38.1, "mount_pattern_span_mm": 47.14, "mount_hole_dia_mm": 5.0},
        cad={"gltf_uri": "cad/iCL57-23.glb", "units": "metre"},
        part_frame={"units": "millimetre", "drawing_to_cad": {"scale": 1.0, "rotation": "identity", "translation": [0,0,0]}},
        ports=ports,
        port_groups=groups
    )
    save_part(pd)

# ============================================================================
# 4. 18T S5M Pulley (HTPA18S5M150-A-H5)
# ============================================================================
def author_pulley18(part_number="HTPA18S5M150-A-H5", bore_mm=5.0):
    bore_r = bore_mm / 2.0
    ports = [
        EngagementPort("bore", "cylindrical", "receiver",
            {"axis": {"origin": [0.0, 0.0, 0.0], "direction": PX},
             "radial_interval_mm": {"min": bore_r, "max": bore_r, "unit": "mm"},
             "axial_interval_mm": {"min": 0.0, "max": 22.0, "unit": "mm"}, "material_side": "inside"},
            semantic_aliases=["shaft_bore"], annotation_status="confirmed"),
        EngagementPort("mount_face", "planar", "contact",
            {"plane": {"origin": [0.0, 0.0, 0.0], "normal": NX}, "boundary_uv_mm": ring_yz(bore_r, 13.75), "material_side": "positive_normal"},
            semantic_aliases=["seating_face"], annotation_status="confirmed"),
        EngagementPort("teeth", "periodic", "external",
            {"subtype": "rotary",
             "support": {"axis": {"origin": [11.0, 0.0, 0.0], "direction": PX}, "radius": 14.3239, "axial_interval_mm": {"min": -7.5, "max": 7.5}},
             "periodicity": {"pitch_mm": 5.0, "count": 18, "active_width_mm": {"min": 15.0, "max": 15.0}},
             "profile": {"family": "S5M"}},
            annotation_status="confirmed")
    ]
    pd = PartDefinition(
        part_number=part_number,
        classification={"catalog_family": "timing_pulley"},
        source={"url": f"misumi:{part_number}", "retrieved_at": "2026-06-25", "brand": "MISUMI"},
        normalized_parameters={"pitch_mm": 5.0, "tooth_count": 18, "bore_mm": bore_mm, "belt_width_mm": 15.0},
        cad={"gltf_uri": f"cad/{part_number}.glb", "units": "metre"},
        part_frame={"units": "millimetre", "drawing_to_cad": {"scale": 1.0, "rotation": "identity", "translation": [0,0,0]}},
        ports=ports,
        port_groups=[]
    )
    save_part(pd)

# ============================================================================
# 5. Base Interface Plate (BASE_INTERFACE_PLATE_REV_A)
# ============================================================================
def author_base():
    ports = [
        EngagementPort("top_face", "planar", "contact",
            {"plane": {"origin": [0.0, 0.0, 20.0], "normal": PZ}, "boundary_uv_mm": ring_xy(47.0, 90.0), "material_side": "negative_normal"},
            semantic_aliases=["column_mounting_face"], annotation_status="confirmed"),
        EngagementPort("bot_face", "planar", "contact",
            {"plane": {"origin": [0.0, 0.0, 0.0], "normal": NZ}, "boundary_uv_mm": ring_xy(47.0, 90.0), "material_side": "positive_normal"},
            annotation_status="confirmed"),
        EngagementPort("outer_ring_seat", "planar", "contact",
            {"plane": {"origin": [0.0, 0.0, 20.0], "normal": PZ}, "boundary_uv_mm": ring_xy(47.0, 90.0), "material_side": "negative_normal"},
            semantic_aliases=["bearing_seat"], annotation_status="confirmed")
    ]
    groups = []
    for i, (x, y) in enumerate(pcd_points(52.5, 8, 22.5), 1):
        ports.append(EngagementPort(f"outer_ring_thread_{i}", "threaded", "internal",
            {"axis": {"origin": [x, y, 20.0], "direction": NZ},
             "axial_interval_mm": {"min": 0.0, "max": 15.0, "unit": "mm"},
             "thread": {"standard": "ISO_metric", "designation": "M5x0.8", "pitch_mm": 0.8, "handedness": "right", "starts": 1}},
            annotation_status="confirmed"))
    groups.append(PortGroup("outer_ring_pattern", "repeated_ports",
        members=[{"port": f"outer_ring_thread_{i}"} for i in range(1, 9)]))
        
    i = 1
    for x in [-60.0, 60.0]:
        for y in [-60.0, 60.0]:
            ports.append(EngagementPort(f"ground_through_{i}", "cylindrical", "receiver",
                {"axis": {"origin": [x, y, 0.0], "direction": PZ},
                 "radial_interval_mm": {"min": 3.3, "max": 3.3, "unit": "mm"},
                 "axial_interval_mm": {"min": 0.0, "max": 20.0, "unit": "mm"}, "material_side": "inside"},
                annotation_status="confirmed"))
            i += 1
    groups.append(PortGroup("ground_pattern", "repeated_ports",
        members=[{"port": f"ground_through_{k}"} for k in range(1, 5)]))

    pd = PartDefinition(
        part_number="BASE_INTERFACE_PLATE_REV_A",
        classification={"catalog_family": "custom_machined", "aliases": ["base_plate"]},
        source={"url": "fabricated", "retrieved_at": "2026-06-25"},
        normalized_parameters={"thickness_mm": 20, "outer_diameter_mm": 180, "central_bore_mm": 94, "bearing_PCD_mm": 105, "bearing_thread": "M5", "ground_pattern_square_mm": 120},
        cad={"gltf_uri": "cad/BASE_INTERFACE_PLATE_REV_A.glb", "units": "metre"},
        part_frame={"units": "millimetre", "drawing_to_cad": {"scale": 1.0, "rotation": "identity", "translation": [0,0,0]}},
        ports=ports,
        port_groups=groups
    )
    save_part(pd)

# ============================================================================
# 6. J1 Output Hub (J1_OUTPUT_HUB_REV_A)
# ============================================================================
def author_hub1():
    ports = [
        EngagementPort("shaft", "cylindrical", "insert",
            {"axis": {"origin": [0.0, 0.0, 0.0], "direction": PZ},
             "radial_interval_mm": {"min": 15.0, "max": 15.0, "unit": "mm"},
             "axial_interval_mm": {"min": 0.0, "max": 40.0, "unit": "mm"}, "material_side": "outside"},
            semantic_aliases=["drive_shaft"], annotation_status="confirmed"),
        EngagementPort("pulley_pilot", "cylindrical", "insert",
            {"axis": {"origin": [0.0, 0.0, -22.0], "direction": PZ},
             "radial_interval_mm": {"min": 25.0, "max": 25.0, "unit": "mm"},
             "axial_interval_mm": {"min": 0.0, "max": 22.0, "unit": "mm"}, "material_side": "outside"},
            semantic_aliases=["H50_pilot", "pulley_locating_boss"], annotation_status="confirmed"),
        EngagementPort("pulley_seat", "planar", "contact",
            {"plane": {"origin": [0.0, 0.0, 0.0], "normal": NZ},
             "boundary_uv_mm": ring_xy(25.0, 46.0), "material_side": "positive_normal"},
            semantic_aliases=["pulley_mount_face"], annotation_status="confirmed"),
        EngagementPort("inner_race_boss", "planar", "contact",
            {"plane": {"origin": [0.0, 0.0, 40.0], "normal": NZ}, "boundary_uv_mm": ring_xy(15.0, 38.0), "material_side": "positive_normal"},
            semantic_aliases=["bearing_contact_land"], annotation_status="confirmed"),
        EngagementPort("relieved_underside", "planar", "contact",
            {"plane": {"origin": [0.0, 0.0, 45.0], "normal": NZ}, "boundary_uv_mm": ring_xy(38.0, 55.0), "material_side": "positive_normal"},
            semantic_aliases=["flange_underside_relief"], annotation_status="confirmed"),
        EngagementPort("link1_seat", "planar", "contact",
            {"plane": {"origin": [0.0, 0.0, 55.0], "normal": PZ}, "boundary_uv_mm": ring_xy(15.0, 55.0), "material_side": "negative_normal"},
            semantic_aliases=["flange_top_face"], annotation_status="confirmed")
    ]
    groups = []
    for i, (x, y) in enumerate(pcd_points(32.5, 8, 22.5), 1):
        ports.append(EngagementPort(f"inner_race_through_{i}", "cylindrical", "receiver",
            {"axis": {"origin": [x, y, 40.0], "direction": PZ},
             "radial_interval_mm": {"min": 2.75, "max": 2.75, "unit": "mm"},
             "axial_interval_mm": {"min": 0.0, "max": 15.0, "unit": "mm"}, "material_side": "inside"},
            annotation_status="confirmed"))
    groups.append(PortGroup("inner_race_pattern", "repeated_ports",
        members=[{"port": f"inner_race_through_{i}"} for i in range(1, 9)]))

    for i, (x, y) in enumerate(pcd_points(42.5, 4, 0.0), 1):
        ports.append(EngagementPort(f"pulley_thread_{i}", "threaded", "internal",
            {"axis": {"origin": [x, y, 0.0], "direction": PZ},
             "axial_interval_mm": {"min": 0.0, "max": 8.0, "unit": "mm"},
             "thread": {"standard": "ISO_metric", "designation": "M5x0.8", "pitch_mm": 0.8, "handedness": "right", "starts": 1}},
            annotation_status="confirmed"))
    groups.append(PortGroup("pulley_pattern", "repeated_ports",
        members=[{"port": f"pulley_thread_{i}"} for i in range(1, 5)]))
        
    for i, (x, y) in enumerate(pcd_points(45.0, 6, 0.0), 1):
        ports.append(EngagementPort(f"link1_thread_{i}", "threaded", "internal",
            {"axis": {"origin": [x, y, 55.0], "direction": NZ},
             "axial_interval_mm": {"min": 0.0, "max": 6.0, "unit": "mm"},
             "thread": {"standard": "ISO_metric", "designation": "M6x1.0", "pitch_mm": 1.0, "handedness": "right", "starts": 1}},
            annotation_status="confirmed"))
    groups.append(PortGroup("link1_pattern", "repeated_ports",
        members=[{"port": f"link1_thread_{i}"} for i in range(1, 7)]))

    pd = PartDefinition(
        part_number="J1_OUTPUT_HUB_REV_A",
        classification={"catalog_family": "custom_machined", "aliases": ["shoulder_hub"]},
        source={"url": "fabricated", "retrieved_at": "2026-06-25"},
        normalized_parameters={"shaft_dia_mm": 30, "flange_dia_mm": 110, "bearing_land_dia_mm": 76, "bearing_PCD_mm": 65, "pulley_pilot_dia_mm": 50, "pulley_PCD_mm": 85, "pulley_thread": "M5", "link1_PCD_mm": 90, "link1_thread": "M6"},
        cad={"gltf_uri": "cad/J1_OUTPUT_HUB_REV_A.glb", "units": "metre"},
        part_frame={"units": "millimetre", "drawing_to_cad": {"scale": 1.0, "rotation": "identity", "translation": [0,0,0]}},
        ports=ports,
        port_groups=groups
    )
    save_part(pd)

# ============================================================================
# 7. Link 1 (LINK_1_REV_A)
# ============================================================================
def author_link1():
    nema17_bnd = {"outer": [[-21.0, -21.0], [21.0, -21.0], [21.0, 21.0], [-21.0, 21.0]], "holes": []}
    ports = [
        EngagementPort("j1_mounting_face", "planar", "contact",
            {"plane": {"origin": [0.0, 0.0, 0.0], "normal": NZ}, "boundary_uv_mm": ring_xy(22.5, 60.0), "material_side": "positive_normal"},
            annotation_status="confirmed"),
        EngagementPort("j1_top_face", "planar", "contact",
            {"plane": {"origin": [0.0, 0.0, 20.0], "normal": PZ}, "boundary_uv_mm": ring_xy(22.5, 60.0), "material_side": "negative_normal"},
            semantic_aliases=["j1_screw_head_face"], annotation_status="confirmed"),
        EngagementPort("j2_bearing_seat", "planar", "contact",
            {"plane": {"origin": [300.0, 0.0, 0.0], "normal": NZ}, "boundary_uv_mm": ring_xy(37.5, 55.0), "material_side": "positive_normal"},
            annotation_status="confirmed"),
        EngagementPort("j2_forbidden_ring", "planar", "contact",
            {"plane": {"origin": [300.0, 0.0, 0.0], "normal": NZ}, "boundary_uv_mm": ring_xy(17.5, 23.5), "material_side": "positive_normal"},
            annotation_status="confirmed"),
        EngagementPort("motor_bracket_seat", "planar", "contact",
            {"plane": {"origin": [105.4, 0.0, 0.0], "normal": NZ}, "boundary_uv_mm": rect(-40.0, 40.0, -30.0, 30.0), "material_side": "positive_normal"},
            semantic_aliases=["nema17_hanger_underface"], annotation_status="confirmed"),
        EngagementPort("motor_bracket_top_face", "planar", "contact",
            {"plane": {"origin": [105.4, 0.0, 20.0], "normal": PZ}, "boundary_uv_mm": rect(-40.0, 40.0, -30.0, 30.0), "material_side": "negative_normal"},
            semantic_aliases=["nema17_hanger_screw_head_face"], annotation_status="confirmed"),
        EngagementPort("nema17_seat", "planar", "contact",
            {"plane": {"origin": [105.4, 0.0, 20.0], "normal": PZ}, "boundary_uv_mm": nema17_bnd, "material_side": "negative_normal"},
            annotation_status="confirmed")
    ]
    groups = []
    for i, (x, y) in enumerate(pcd_points(45.0, 6, 0.0), 1):
        ports.append(EngagementPort(f"j1_through_{i}", "cylindrical", "receiver",
            {"axis": {"origin": [x, y, 0.0], "direction": PZ},
             "radial_interval_mm": {"min": 3.3, "max": 3.3, "unit": "mm"},
             "axial_interval_mm": {"min": 0.0, "max": 20.0, "unit": "mm"}, "material_side": "inside"},
            annotation_status="confirmed"))
    groups.append(PortGroup("j1_mounting_pattern", "repeated_ports",
        members=[{"port": f"j1_through_{i}"} for i in range(1, 7)]))
        
    for i, (x, y) in enumerate(pcd_points(41.5, 8, 22.5), 1):
        ports.append(EngagementPort(f"j2_thread_{i}", "threaded", "internal",
            {"axis": {"origin": [300.0 + x, y, 0.0], "direction": PZ},
             "axial_interval_mm": {"min": 0.0, "max": 6.0, "unit": "mm"},
             "thread": {"standard": "ISO_metric", "designation": "M4x0.7", "pitch_mm": 0.7, "handedness": "right", "starts": 1}},
            annotation_status="confirmed"))
    groups.append(PortGroup("j2_bearing_pattern", "repeated_ports",
        members=[{"port": f"j2_thread_{i}"} for i in range(1, 9)]))
        
    i = 1
    for dx in [-15.5, 15.5]:
        for dy in [-15.5, 15.5]:
            ports.append(EngagementPort(f"slot_through_{i}", "swept_profile", "receiver",
                {"axis": {"origin": [105.4 + dx, dy, 0.0], "direction": PZ},
                 "sweep_path": {"type": "line", "points": [[105.4 + dx, dy, 0.0], [105.4 + dx, dy, 20.0]]},
                 "section_frame": {"origin": [105.4 + dx, dy, 0.0], "x_axis": PX, "y_axis": PY, "z_axis": PZ},
                 "section_profile_uv_mm": {"outer": [[-6.0, -1.6], [6.0, -1.6], [6.0, 1.6], [-6.0, 1.6]], "holes": []},
                 "sweep_interval_mm": {"min": 0.0, "max": 20.0, "unit": "mm"},
                 "material_side": "inside_profile"},
                annotation_status="confirmed"))
            i += 1
    groups.append(PortGroup("nema17_pattern", "repeated_ports",
        members=[{"port": f"slot_through_{k}"} for k in range(1, 5)]))

    pd = PartDefinition(
        part_number="LINK_1_REV_A",
        classification={"catalog_family": "custom_machined", "aliases": ["link1"]},
        source={"url": "fabricated", "retrieved_at": "2026-06-25"},
        normalized_parameters={"length_mm": 300, "thickness_mm": 20, "j1_PCD_mm": 90, "j2_PCD_mm": 83, "j2_thread": "M4"},
        cad={"gltf_uri": "cad/LINK_1_REV_A.glb", "units": "metre"},
        part_frame={"units": "millimetre", "drawing_to_cad": {"scale": 1.0, "rotation": "identity", "translation": [0,0,0]}},
        ports=ports,
        port_groups=groups
    )
    save_part(pd)

# ============================================================================
# 8. J2 Custom Pulley/Flange (J2_CUSTOM_PULLEY_REV_A)
# ============================================================================
def author_pulley2():
    ports = [
        EngagementPort("bore", "cylindrical", "receiver",
            {"axis": {"origin": [0.0, 0.0, 0.0], "direction": PZ},
             "radial_interval_mm": {"min": 15.0, "max": 15.0, "unit": "mm"},
             "axial_interval_mm": {"min": 0.0, "max": 17.0, "unit": "mm"}, "material_side": "inside"},
            semantic_aliases=["center_bore"], annotation_status="confirmed"),
        EngagementPort("upper_race_seat", "planar", "contact",
            {"plane": {"origin": [0.0, 0.0, 17.0], "normal": PZ}, "boundary_uv_mm": ring_xy(17.5, 23.5), "material_side": "negative_normal"},
            semantic_aliases=["bearing_seating_face"], annotation_status="confirmed"),
        EngagementPort("upper_forbidden_ring", "planar", "contact",
            {"plane": {"origin": [0.0, 0.0, 17.0], "normal": PZ}, "boundary_uv_mm": ring_xy(27.5, 47.5), "material_side": "negative_normal"},
            annotation_status="confirmed"),
        EngagementPort("link2_seat", "planar", "contact",
            {"plane": {"origin": [0.0, 0.0, 0.0], "normal": NZ}, "boundary_uv_mm": ring_xy(15.0, 47.15), "material_side": "positive_normal"},
            annotation_status="confirmed"),
        EngagementPort("teeth", "periodic", "external",
            {"subtype": "rotary",
             "support": {"axis": {"origin": [0.0, 0.0, 0.0], "direction": PZ}, "radius": 47.7465, "axial_interval_mm": {"min": 0.0, "max": 15.0}},
             "periodicity": {"pitch_mm": 5.0, "count": 60, "active_width_mm": {"min": 15.0, "max": 15.0}},
             "profile": {"family": "S5M"}},
            annotation_status="confirmed")
    ]
    groups = []
    for i, (x, y) in enumerate(pcd_points(22.5, 8, 22.5), 1):
        ports.append(EngagementPort(f"upper_race_through_{i}", "cylindrical", "receiver",
            {"axis": {"origin": [x, y, 17.0], "direction": NZ},
             "radial_interval_mm": {"min": 2.25, "max": 2.25, "unit": "mm"},
             "axial_interval_mm": {"min": 0.0, "max": 17.0, "unit": "mm"}, "material_side": "inside"},
            annotation_status="confirmed"))
    groups.append(PortGroup("upper_race_pattern", "repeated_ports",
        members=[{"port": f"upper_race_through_{i}"} for i in range(1, 9)]))
        
    for i, (x, y) in enumerate(pcd_points(35.0, 6, 0.0), 1):
        ports.append(EngagementPort(f"link2_thread_{i}", "threaded", "internal",
            {"axis": {"origin": [x, y, 0.0], "direction": PZ},
             "axial_interval_mm": {"min": 0.0, "max": 10.0, "unit": "mm"},
             "thread": {"standard": "ISO_metric", "designation": "M5x0.8", "pitch_mm": 0.8, "handedness": "right", "starts": 1}},
            annotation_status="confirmed"))
    groups.append(PortGroup("link2_pattern", "repeated_ports",
        members=[{"port": f"link2_thread_{i}"} for i in range(1, 7)]))

    pd = PartDefinition(
        part_number="J2_CUSTOM_PULLEY_REV_A",
        classification={"catalog_family": "custom_machined", "aliases": ["elbow_pulley"]},
        source={"url": "fabricated", "retrieved_at": "2026-06-25"},
        normalized_parameters={"pitch_mm": 5.0, "tooth_count": 60, "thickness_mm": 17, "bearing_PCD_mm": 45, "link2_PCD_mm": 70, "link2_thread": "M5"},
        cad={"gltf_uri": "cad/J2_CUSTOM_PULLEY_REV_A.glb", "units": "metre"},
        part_frame={"units": "millimetre", "drawing_to_cad": {"scale": 1.0, "rotation": "identity", "translation": [0,0,0]}},
        ports=ports,
        port_groups=groups
    )
    save_part(pd)

# ============================================================================
# 9. Link 2 (LINK_2_REV_A)
# ============================================================================
def author_link2():
    tool_bnd = {"outer": [[-30.0, -30.0], [30.0, -30.0], [30.0, 30.0], [-30.0, 30.0]], "holes": []}
    ports = [
        EngagementPort("j2_mounting_face", "planar", "contact",
            {"plane": {"origin": [0.0, 0.0, 15.0], "normal": PZ}, "boundary_uv_mm": ring_xy(15.0, 45.0), "material_side": "negative_normal"},
            annotation_status="confirmed"),
        EngagementPort("j2_bottom_face", "planar", "contact",
            {"plane": {"origin": [0.0, 0.0, 0.0], "normal": NZ}, "boundary_uv_mm": ring_xy(15.0, 45.0), "material_side": "positive_normal"},
            semantic_aliases=["j2_screw_head_face"], annotation_status="confirmed"),
        EngagementPort("tool_face", "planar", "contact",
            {"plane": {"origin": [300.0, 0.0, 0.0], "normal": NZ}, "boundary_uv_mm": tool_bnd, "material_side": "positive_normal"},
            semantic_aliases=["tool_mounting_face"], annotation_status="confirmed")
    ]
    groups = []
    for i, (x, y) in enumerate(pcd_points(35.0, 6, 0.0), 1):
        ports.append(EngagementPort(f"j2_through_{i}", "cylindrical", "receiver",
            {"axis": {"origin": [x, y, 15.0], "direction": NZ},
             "radial_interval_mm": {"min": 2.75, "max": 2.75, "unit": "mm"},
             "axial_interval_mm": {"min": 0.0, "max": 15.0, "unit": "mm"}, "material_side": "inside"},
            annotation_status="confirmed"))
    groups.append(PortGroup("j2_mounting_pattern", "repeated_ports",
        members=[{"port": f"j2_through_{i}"} for i in range(1, 7)]))
        
    i = 1
    for dx in [-20.0, 20.0]:
        for dy in [-20.0, 20.0]:
            ports.append(EngagementPort(f"tool_thread_{i}", "threaded", "internal",
                {"axis": {"origin": [300.0 + dx, dy, 0.0], "direction": PZ},
                 "axial_interval_mm": {"min": 0.0, "max": 12.0, "unit": "mm"},
                 "thread": {"standard": "ISO_metric", "designation": "M5x0.8", "pitch_mm": 0.8, "handedness": "right", "starts": 1}},
                annotation_status="confirmed"))
            i += 1
    groups.append(PortGroup("tool_pattern", "repeated_ports",
        members=[{"port": f"tool_thread_{k}"} for k in range(1, 5)]))

    pd = PartDefinition(
        part_number="LINK_2_REV_A",
        classification={"catalog_family": "custom_machined", "aliases": ["link2"]},
        source={"url": "fabricated", "retrieved_at": "2026-06-25"},
        normalized_parameters={"length_mm": 300, "thickness_mm": 15, "j2_PCD_mm": 70, "tool_pattern_square_mm": 40, "tool_thread": "M5"},
        cad={"gltf_uri": "cad/LINK_2_REV_A.glb", "units": "metre"},
        part_frame={"units": "millimetre", "drawing_to_cad": {"scale": 1.0, "rotation": "identity", "translation": [0,0,0]}},
        ports=ports,
        port_groups=groups
    )
    save_part(pd)

# ============================================================================
# 10. J2 outboard NEMA17 motor hanger (J2_MOTOR_HANGER_REV_A)
# ============================================================================
def author_j2_motor_hanger():
    plate = rect(-45.0, 45.0, -35.0, 105.0)
    motor_pad = rect(-28.0, 28.0, -28.0, 28.0)
    link_pad = rect(-38.0, 38.0, -25.0, 25.0)
    ports = [
        EngagementPort("motor_face", "planar", "contact",
            {"plane": {"origin": [0.0, 0.0, 6.0], "normal": PZ}, "boundary_uv_mm": motor_pad, "material_side": "negative_normal"},
            semantic_aliases=["nema17_front_plate"], annotation_status="confirmed"),
        EngagementPort("link_seat", "planar", "contact",
            {"plane": {"origin": [0.0, 75.0, 6.0], "normal": PZ}, "boundary_uv_mm": link_pad, "material_side": "negative_normal"},
            semantic_aliases=["link1_underface_seat"], annotation_status="confirmed"),
        EngagementPort("bottom_face", "planar", "contact",
            {"plane": {"origin": [0.0, 0.0, 0.0], "normal": NZ}, "boundary_uv_mm": plate, "material_side": "positive_normal"},
            semantic_aliases=["screw_head_face"], annotation_status="confirmed"),
    ]
    groups = []
    motor_pts = [(-15.5, 15.5), (-15.5, -15.5), (15.5, 15.5), (15.5, -15.5)]
    for i, (x, y) in enumerate(motor_pts, 1):
        ports.append(EngagementPort(f"motor_through_{i}", "cylindrical", "receiver",
            {"axis": {"origin": [x, y, 6.0], "direction": NZ},
             "radial_interval_mm": {"min": 1.7, "max": 1.7, "unit": "mm"},
             "axial_interval_mm": {"min": 0.0, "max": 6.0, "unit": "mm"}, "material_side": "inside"},
            annotation_status="confirmed"))
    groups.append(PortGroup("motor_mount_pattern", "repeated_ports",
        members=[{"port": f"motor_through_{i}"} for i in range(1, 5)]))

    link_pts = [(-15.5, 59.5), (-15.5, 90.5), (15.5, 59.5), (15.5, 90.5)]
    for i, (x, y) in enumerate(link_pts, 1):
        ports.append(EngagementPort(f"link_thread_{i}", "threaded", "internal",
            {"axis": {"origin": [x, y, 6.0], "direction": NZ},
             "axial_interval_mm": {"min": 0.0, "max": 6.0, "unit": "mm"},
             "thread": {"standard": "ISO_metric", "designation": "M3x0.5", "pitch_mm": 0.5, "handedness": "right", "starts": 1}},
            annotation_status="confirmed"))
    groups.append(PortGroup("link_clamp_pattern", "repeated_ports",
        members=[{"port": f"link_thread_{i}"} for i in range(1, 5)]))

    pd = PartDefinition(
        part_number="J2_MOTOR_HANGER_REV_A",
        classification={"catalog_family": "custom_motor_hanger", "broader_families": ["structural_bracket"]},
        source={"url": "custom_drawing:J2_MOTOR_HANGER_REV_A", "retrieved_at": "2026-06-26", "brand": "AssemblyBot"},
        normalized_parameters={"material": "6061-T6", "thickness_mm": 6.0, "motor_frame": "NEMA17", "link_attachment": "4x_M3"},
        cad={"gltf_uri": "cad/J2_MOTOR_HANGER_REV_A.glb", "units": "metre"},
        part_frame={"units": "millimetre", "drawing_to_cad": {"scale": 1.0, "rotation": "identity", "translation": [0,0,0]}},
        ports=ports,
        port_groups=groups
    )
    save_part(pd)

# ============================================================================
# 11. J1 NEMA23 motor bridge (J1_MOTOR_BRIDGE_REV_A)
# ============================================================================
def author_j1_motor_bridge():
    bridge_height = 26.1
    base_pad = rect(-170.0, 45.0, -72.0, 72.0)
    motor_pad = rect(-36.0, 36.0, -36.0, 36.0)
    ports = [
        EngagementPort("motor_face", "planar", "contact",
            {"plane": {"origin": [0.0, 0.0, 0.0], "normal": NZ}, "boundary_uv_mm": motor_pad, "material_side": "positive_normal"},
            semantic_aliases=["nema23_front_plate"], annotation_status="confirmed"),
        EngagementPort("base_seat", "planar", "contact",
            {"plane": {"origin": [0.0, 0.0, bridge_height], "normal": PZ}, "boundary_uv_mm": base_pad, "material_side": "negative_normal"},
            semantic_aliases=["base_underface_seat"], annotation_status="confirmed"),
    ]
    groups = []
    for i, (x, y) in enumerate([(-23.57, -23.57), (-23.57, 23.57), (23.57, -23.57), (23.57, 23.57)], 1):
        ports.append(EngagementPort(f"motor_thread_{i}", "threaded", "internal",
            {"axis": {"origin": [x, y, 0.0], "direction": NZ},
             "axial_interval_mm": {"min": 0.0, "max": 6.0, "unit": "mm"},
             "thread": {"standard": "ISO_metric", "designation": "M5x0.8", "pitch_mm": 0.8, "handedness": "right", "starts": 1}},
            annotation_status="confirmed"))
    groups.append(PortGroup("motor_mount_pattern", "repeated_ports",
        members=[{"port": f"motor_thread_{i}"} for i in range(1, 5)]))

    # Base ground holes are at world (+/-60,+/-60); bridge local origin is at the motor.
    for i, (x, y) in enumerate([(-155.314, -60.0), (-155.314, 60.0), (-35.314, -60.0), (-35.314, 60.0)], 1):
        ports.append(EngagementPort(f"base_thread_{i}", "threaded", "internal",
            {"axis": {"origin": [x, y, bridge_height], "direction": NZ},
             "axial_interval_mm": {"min": 0.0, "max": 6.0, "unit": "mm"},
             "thread": {"standard": "ISO_metric", "designation": "M6x1.0", "pitch_mm": 1.0, "handedness": "right", "starts": 1}},
            annotation_status="confirmed"))
    groups.append(PortGroup("base_mount_pattern", "repeated_ports",
        members=[{"port": f"base_thread_{i}"} for i in range(1, 5)]))

    pd = PartDefinition(
        part_number="J1_MOTOR_BRIDGE_REV_A",
        classification={"catalog_family": "custom_motor_bridge", "broader_families": ["structural_bracket"]},
        source={"url": "custom_drawing:J1_MOTOR_BRIDGE_REV_A", "retrieved_at": "2026-06-26", "brand": "AssemblyBot"},
        normalized_parameters={"material": "6061-T6", "motor_frame": "NEMA23", "base_attachment": "4x_M6"},
        cad={"gltf_uri": "cad/J1_MOTOR_BRIDGE_REV_A.glb", "units": "metre"},
        part_frame={"units": "millimetre", "drawing_to_cad": {"scale": 1.0, "rotation": "identity", "translation": [0,0,0]}},
        ports=ports,
        port_groups=groups
    )
    save_part(pd)

def author_set_screw(d_shank, pitch, l_shank):
    pn = f"DIN913-M{d_shank}x{pitch}-{l_shank}"
    ports = [
        EngagementPort("thread", "threaded", "external",
            {"axis": {"origin": [0.0, 0.0, 0.0], "direction": PZ},
             "axial_interval_mm": {"min": 0.0, "max": float(l_shank), "unit": "mm"},
             "thread": {"standard": "ISO_metric", "designation": f"M{d_shank}x{pitch}", "pitch_mm": pitch,
                        "handedness": "right", "starts": 1,
                        "major_diameter_mm": {"min": float(d_shank) - 0.2, "max": float(d_shank)}}},
            semantic_aliases=["grub_screw_thread"], annotation_status="confirmed")
    ]
    pd = PartDefinition(
        part_number=pn,
        classification={"catalog_family": "socket_set_screw", "broader_families": ["fastener", "standard_part"], "generative": True},
        source={"standard": "DIN 913 / ISO 4026", "retrieved_at": "2026-06-26"},
        normalized_parameters={"thread_designation": f"M{d_shank}x{pitch}", "nominal_length_mm": float(l_shank), "shank_diameter_mm": float(d_shank)},
        cad={"gltf_uri": f"cad/{pn}.glb", "units": "metre"},
        part_frame={"units": "millimetre", "drawing_to_cad": {"scale": 1.0, "rotation": "identity", "translation": [0,0,0]}},
        ports=ports,
        port_groups=[]
    )
    save_part(pd)

def author_screw(d_shank, pitch, l_shank, d_head, h_head, *, part_number=None,
                 standard="ISO 4762", catalog_family="socket_head_cap_screw"):
    pn = part_number or f"ISO4762-M{d_shank}x{pitch}-{l_shank}"
    dk_half = d_head / 2.0
    d_half = d_shank / 2.0
    
    ports = [
        EngagementPort("thread", "threaded", "external",
            {"axis": {"origin": [0.0, 0.0, 0.0], "direction": PZ},
             "axial_interval_mm": {"min": -float(l_shank), "max": 0.0, "unit": "mm"},
             "thread": {"standard": "ISO_metric", "designation": f"M{d_shank}x{pitch}", "pitch_mm": pitch, "handedness": "right", "starts": 1,
                        "major_diameter_mm": {"min": float(d_shank) - 0.2, "max": float(d_shank)}}},
            semantic_aliases=["screw_thread"], annotation_status="confirmed"),
        EngagementPort("head_seat", "planar", "contact",
            {"plane": {"origin": [0.0, 0.0, 0.0], "normal": NZ},
             "boundary_uv_mm": {"outer": [[-dk_half, -dk_half], [dk_half, -dk_half], [dk_half, dk_half], [-dk_half, dk_half]],
                                "holes": [[[-d_half, -d_half], [d_half, -d_half], [d_half, d_half], [-d_half, d_half]]]},
             "material_side": "positive_normal"},
            semantic_aliases=["head_underside", "axial_stop"], annotation_status="confirmed")
    ]
    
    pd = PartDefinition(
        part_number=pn,
        classification={"catalog_family": catalog_family, "broader_families": ["fastener", "standard_part"], "generative": True},
        source={"standard": standard, "retrieved_at": "2026-06-25"},
        normalized_parameters={"thread_designation": f"M{d_shank}x{pitch}", "nominal_length_mm": float(l_shank), "shank_diameter_mm": float(d_shank),
                               "head_diameter_mm": float(d_head), "head_height_mm": float(h_head)},
        cad={"gltf_uri": f"cad/{pn}.glb", "units": "metre"},
        part_frame={"units": "millimetre", "drawing_to_cad": {"scale": 1.0, "rotation": "identity", "translation": [0,0,0]}},
        ports=ports,
        port_groups=[]
    )
    save_part(pd)

def main():
    author_ru66()
    author_nema17()
    author_nema23()
    author_pulley18()
    author_base()
    author_hub1()
    author_link1()
    author_pulley2()
    author_link2()
    author_j2_motor_hanger()
    author_j1_motor_bridge()
    # Screws
    author_pulley18("HTPA18S5M150-A-H8", 8.0)
    author_set_screw(4, 0.7, 6)
    author_screw(3, 0.5, 10, 5.5, 3.0)
    author_screw(3, 0.5, 30, 5.5, 3.0)
    author_screw(5, 0.8, 90, 8.5, 5.0)
    author_screw(4, 0.7, 20, 7.0, 2.0, part_number="ULTRA_LOW_HEAD_M4x0.7-20",
                 standard="ultra-low-head socket screw", catalog_family="ultra_low_head_socket_screw")
    author_screw(4, 0.7, 20, 7.0, 4.0)
    author_screw(4, 0.7, 25, 7.0, 4.0)
    author_screw(5, 0.8, 20, 8.5, 5.0)
    author_screw(5, 0.8, 25, 8.5, 5.0)
    author_screw(5, 0.8, 30, 8.5, 5.0)
    author_screw(6, 1.0, 30, 10.0, 6.0)
    print("All library JSON entries successfully authored.")

if __name__ == "__main__":
    main()
