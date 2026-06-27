"""Rung 4 -- 2R Belt-Reduced Robot Arm Assembly.

Assembles the complete 2R robot arm from custom and catalog parts,
binds all joints and fasteners to v2 templates, computes the belts,
solves poses, runs the validation gates, and renders the LOOK views.
"""
from __future__ import annotations
import json, math, os
from pathlib import Path
import numpy as np

from ontology.schema_v2 import PartDefinition
from ontology.templates import TEMPLATES
from ontology import load_path as LP

ROOT = Path(__file__).resolve().parent.parent
OUT, LIBV2, CAD = ROOT / "projects" / "two_joint_arm_assembly" / "out", ROOT / "library_v2", ROOT / "cad"
OUT.mkdir(parents=True, exist_ok=True)

I = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
# CAD rotations:
# Bearings and pulleys are X-native (axis along local X).
# Rotates local X (pulley/bearing axis) -> world Z.
R_XZ = [[0, 0, -1], [0, 1, 0], [1, 0, 0]]
# Rotates local X -> world -Z (for inverted bearings)
R_XZ_INV = [[0, 0, 1], [0, 1, 0], [-1, 0, 0]]
# Flips local Z axis (180 deg around X axis) for upward-pointing screws
R_flip = [[1, 0, 0], [0, -1, 0], [0, 0, -1]]

def load(stem):
    return PartDefinition.from_json(json.loads((LIBV2 / f"{stem}.json").read_text()))

def belt_loop(c1, R1, c2, R2, z, n=64):
    c1 = np.asarray(c1, float); c2 = np.asarray(c2, float)
    D = float(np.linalg.norm(c2 - c1)); phi = math.atan2(*(c2 - c1)[::-1])
    gamma = math.asin((R1 - R2) / D); alpha = math.pi / 2 - gamma
    def pt(c, R, ang): return [c[0] + R * math.cos(ang), c[1] + R * math.sin(ang), z]
    pts = []
    for k in range(n + 1):
        a = (phi + alpha) + (2 * math.pi - 2 * alpha) * k / n
        pts.append(pt(c1, R1, a))
    for k in range(n + 1):
        a = (phi - alpha) + (2 * alpha) * k / n
        pts.append(pt(c2, R2, a))
    return np.asarray(pts)

def build_belt_mesh(pts, width=15.0, thick=1.5):
    import trimesh
    t, w = thick / 2000.0, width / 2000.0
    poly = trimesh.path.polygons.Polygon([(-t, -w), (t, -w), (t, w), (-t, w)])
    path = np.vstack([pts, pts[0]]) / 1000.0
    try:
        return trimesh.creation.sweep_polygon(poly, path)
    except Exception:
        return None

def pcd_points(r, n=8, start=22.5):
    pts = []
    for k in range(n):
        ang = math.radians(start + (360.0 / n) * k)
        pts.append((r * math.cos(ang), r * math.sin(ang)))
    return pts

def main():
    print("=== RUNG 4 -- 2R BELT-REDUCED ROBOT ARM ASSEMBLY ===\n")
    
    # 1. Load Part Definitions
    lib = {
        "p_base": load("BASE_INTERFACE_PLATE_REV_A"),
        "p_brg1": load("RU85UUC0"),
        "p_hub1": load("J1_OUTPUT_HUB_REV_A"),
        "p_pul72": load("HTPA72S5M150-A-H50-KFC85-K5.5"),
        "p_pul18_j1": load("HTPA18S5M150-A-H8"),
        "p_j1_mbridge": load("J1_MOTOR_BRIDGE_REV_A"),
        "p_motor23": load("iCL57-23"),
        
        "p_link1": load("LINK_1_REV_A"),
        "p_brg2": load("RU66UUC0"),
        "p_pul60": load("J2_CUSTOM_PULLEY_REV_A"),
        "p_pul18_j2": load("HTPA18S5M150-A-H5"),
        "p_j2_mhanger": load("J2_MOTOR_HANGER_REV_A"),
        "p_motor17": load("iCL42-06"),
        
        "p_link2": load("LINK_2_REV_A"),
    }
    
    # Pulley pitches and radii
    pitch = 5.0
    PR72 = 72 * pitch / (2 * math.pi)
    PR60 = 60 * pitch / (2 * math.pi)
    PR18 = 18 * pitch / (2 * math.pi)
    
    # Center distances (snapped to S5M belts)
    D_j1 = 95.314
    D_j2 = 194.631
    M17_Y = -75.0
    
    # Poses & Placements
    # World frame: J1 pivot = (0,0,0). Base plate top face = Z=20.
    pl = {
        "p_base":      {"R": I,    "t_mm": [0.0, 0.0, 0.0]},                     # base top at Z=20, bot at Z=0
        "p_brg1":      {"R": R_XZ, "t_mm": [0.0, 0.0, 20.0]},                  # RU85 outer sits on base top face (Z=20)
        "p_hub1":      {"R": I,    "t_mm": [0.0, 0.0, -5.0]},                   # hub contact land bottom (local Z=40) at RU85 inner top (world Z=35)
        "p_pul72":     {"R": R_XZ, "t_mm": [0.0, 0.0, -27.0]},                 # top face seats at hub underside; teeth centerline Z=-16
        "p_pul18_j1":  {"R": R_XZ, "t_mm": [D_j1, 0.0, -27.0]},                # 18T pulley centerline aligned with 72T
        "p_j1_mbridge": {"R": I,   "t_mm": [D_j1, 0.0, -26.1]},                # NEMA23 bridge from base underside to motor face
        "p_motor23":   {"R": I,    "t_mm": [D_j1, 0.0, -106.1]},               # NEMA 23 front face clears the lower edge of the J1 belt
        
        "p_link1":     {"R": I,    "t_mm": [0.0, 0.0, 50.0]},                  # Link 1 proximal face at J1 hub top (Z=50)
        "p_brg2":      {"R": R_XZ_INV, "t_mm": [300.0, 0.0, 50.0]},            # RU66 outer seats beneath Link 1 bottom face (Z=50)
        "p_pul60":     {"R": I,    "t_mm": [300.0, 0.0, 18.0]},                # J2 custom pulley seats on RU66 inner ring bottom (Z=35)
        "p_pul18_j2":  {"R": R_XZ_INV, "t_mm": [105.4, M17_Y, 36.5]},          # 18T pulley centerline at Z=25.5, outboard of Link 1
        "p_j2_mhanger": {"R": I,   "t_mm": [105.4, M17_Y, 44.0]},              # 6 mm hanger plate under Link 1, cantilevered outboard
        "p_motor17":   {"R": R_flip, "t_mm": [105.4, M17_Y, 90.0]},            # NEMA 17 carried outboard; shaft points down to the belt plane
        
        "p_link2":     {"R": I,    "t_mm": [300.0, 0.0, 3.0]},                 # Link 2 proximal face seats on custom pulley bottom (Z=18)
    }

    # 2. Build and export belt meshes
    belt_j1 = belt_loop((0.0, 0.0), PR72, (D_j1, 0.0), PR18, -16.0, n=80)
    mesh_j1 = build_belt_mesh(belt_j1)
    if mesh_j1 is not None:
        mesh_j1.export(str(CAD / "belt_s5m_j1.glb"))
        print(f"J1 belt mesh: {len(mesh_j1.vertices)} vertices -> cad/belt_s5m_j1.glb")
        
    belt_j2 = belt_loop((300.0, 0.0), PR60, (105.4, M17_Y), PR18, 25.5, n=80)
    mesh_j2 = build_belt_mesh(belt_j2)
    if mesh_j2 is not None:
        mesh_j2.export(str(CAD / "belt_s5m_j2.glb"))
        print(f"J2 belt mesh: {len(mesh_j2.vertices)} vertices -> cad/belt_s5m_j2.glb")

    # Placements for render-only flexible belts
    pl["p_belt_j1"] = {"R": I, "t_mm": [0.0, 0.0, 0.0]}
    pl["p_belt_j2"] = {"R": I, "t_mm": [0.0, 0.0, 0.0]}

    # 3. Mating Template Bindings (Instances)
    inst = [
        # --- SHOULDER JOINT J1 ---
        # 1) Base -> RU85 Outer Ring
        TEMPLATES["bearing_ring_mount"].bind({
            "plate": "p_base.outer_ring_seat", "ring": "p_brg1.outer_ring_base_face", "forbidden": "p_brg1.inner_ring_base_face",
            "plate_group": "p_base:outer_ring_pattern", "ring_group": "p_brg1:outer_ring_pattern", "screws": "p_base.outer_ring_thread_1"
        }),
        # 2) J1 Hub -> RU85 Inner Ring
        TEMPLATES["bearing_ring_mount"].bind({
            "plate": "p_hub1.inner_race_boss", "ring": "p_brg1.inner_ring_adapter_face", "forbidden": "p_brg1.outer_ring_adapter_face",
            "plate_group": "p_hub1:inner_race_pattern", "ring_group": "p_brg1:inner_ring_pattern", "screws": "p_brg1.inner_thread_1"
        }),
        # 3) Link 1 -> J1 Hub
        TEMPLATES["pilot_located_bolted_hub"].bind({
            "hub": "p_link1.j1_mounting_face", "pilot": "p_hub1.shaft",
            "hub_seat": "p_link1.j1_mounting_face", "seat": "p_hub1.link1_seat",
            "hub_group": "p_link1:j1_mounting_pattern", "seat_group": "p_hub1:link1_pattern"
        }),
        # 4) 72T output pulley -> J1 hub REV_B underside
        TEMPLATES["pilot_located_through_bolted_hub"].bind({
            "hub": "p_pul72.bore", "pilot": "p_hub1.pulley_pilot",
            "hub_seat": "p_pul72.top_mount_face", "seat": "p_hub1.pulley_seat",
            "hub_group": "p_pul72:mount_pattern", "seat_group": "p_hub1:pulley_pattern"
        }),
        # 5) NEMA23 bridge -> base underside
        TEMPLATES["bounded_bolt_pattern_seat"].bind({
            "plate": "p_j1_mbridge.base_seat", "seat": "p_base.bot_face",
            "plate_group": "p_j1_mbridge:base_mount_pattern", "seat_group": "p_base:ground_pattern"
        }),
        # 6) NEMA23 motor front face -> bridge plate
        TEMPLATES["bounded_bolt_pattern_seat"].bind({
            "plate": "p_motor23.front_face", "seat": "p_j1_mbridge.motor_face",
            "plate_group": "p_motor23:mount_pattern", "seat_group": "p_j1_mbridge:motor_mount_pattern"
        }),
        
        # --- ELBOW JOINT J2 ---
        # 4) Link 1 -> RU66 Outer Ring (swapped plate/ring for load path direction)
        TEMPLATES["bearing_ring_mount"].bind({
            "plate": "p_brg2.outer_ring_base_face", "ring": "p_link1.j2_bearing_seat", "forbidden": "p_brg2.inner_ring_base_face",
            "plate_group": "p_brg2:outer_ring_pattern", "ring_group": "p_link1:j2_bearing_pattern", "screws": "p_link1.j2_thread_1"
        }),
        # 5) J2 Pulley -> RU66 Inner Ring
        TEMPLATES["bearing_ring_mount"].bind({
            "plate": "p_pul60.upper_race_seat", "ring": "p_brg2.inner_ring_adapter_face", "forbidden": "p_brg2.outer_ring_adapter_face",
            "plate_group": "p_pul60:upper_race_pattern", "ring_group": "p_brg2:inner_ring_pattern", "screws": "p_brg2.inner_thread_1"
        }),
        # 6) Link 2 -> J2 Pulley
        TEMPLATES["pilot_located_bolted_hub"].bind({
            "hub": "p_link2.j2_mounting_face", "pilot": "p_pul60.bore",
            "hub_seat": "p_link2.j2_mounting_face", "seat": "p_pul60.link2_seat",
            "hub_group": "p_link2:j2_mounting_pattern", "seat_group": "p_pul60:link2_pattern"
        }),
        # 7) Outboard NEMA17 hanger -> Link 1 underside, using the Link 1 NEMA17 slot region
        TEMPLATES["bounded_bolt_pattern_seat"].bind({
            "plate": "p_j2_mhanger.link_seat", "seat": "p_link1.motor_bracket_seat",
            "plate_group": "p_j2_mhanger:link_clamp_pattern", "seat_group": "p_link1:nema17_pattern"
        }),
        # 8) NEMA17 motor front face -> hanger plate
        TEMPLATES["bounded_bolt_pattern_seat"].bind({
            "plate": "p_motor17.front_face", "seat": "p_j2_mhanger.motor_face",
            "plate_group": "p_motor17:mount_pattern", "seat_group": "p_j2_mhanger:motor_mount_pattern"
        }),
        # 9) Bearing Internal Revolute Joints
        TEMPLATES["crossed_roller_revolute"].bind({"inner": "p_brg1.bore", "outer": "p_brg1.bore"}),
        TEMPLATES["crossed_roller_revolute"].bind({"inner": "p_brg2.bore", "outer": "p_brg2.bore"}),
        
        # --- DRIVE COUPLINGS & BELT MESHES ---

        # J1 Pulley-Pulley mesh
        TEMPLATES["timing_belt_mesh"].bind({"belt": "p_pul72.teeth", "pulley": "p_pul18_j1.teeth"}),
        TEMPLATES["fixed_hub_on_journal"].bind({"hub": "p_pul18_j1.bore", "journal": "p_motor23.shaft", "set_screw": "f_ss_j1.thread"}),
        # J2 Pulley-Pulley mesh
        TEMPLATES["timing_belt_mesh"].bind({"belt": "p_pul60.teeth", "pulley": "p_pul18_j2.teeth"}),
        TEMPLATES["fixed_hub_on_journal"].bind({"hub": "p_pul18_j2.bore", "journal": "p_motor17.shaft", "set_screw": "f_ss_j2.thread"}),
    ]

    # 4. Instantiate Fasteners and Bind Screws
    lib["f_ss_j1"] = load("DIN913-M4x0.7-6")
    lib["f_ss_j2"] = load("DIN913-M4x0.7-6")

    # 8x M5 Outer J1 screws (Base -> RU85 outer)
    for k, (x, y) in enumerate(pcd_points(52.5, 8, 22.5)):
        fid = f"f_j1_o{k}"
        lib[fid] = load("ISO4762-M5x0.8-25")
        pl[fid] = {"R": I, "t_mm": [x, y, 35.0]} # head seats on RU85 outer top face; thread reaches base tap
        inst.append(TEMPLATES["screw_into_threaded_receiver"].bind({"screw": f"{fid}.thread", "receiver": f"p_base.outer_ring_thread_{k+1}", "bearing": "p_brg1.outer_ring_adapter_face"}))

    # 8x M5 Inner J1 screws (Hub -> RU85 inner)
    for k, (x, y) in enumerate(pcd_points(32.5, 8, 22.5)):
        fid = f"f_j1_i{k}"
        lib[fid] = load("ISO4762-M5x0.8-25")
        pl[fid] = {"R": I, "t_mm": [x, y, 50.0]} # head seats on hub top face; thread reaches RU85 inner tap
        inst.append(TEMPLATES["screw_into_threaded_receiver"].bind({"screw": f"{fid}.thread", "receiver": f"p_brg1.inner_thread_{k+1}", "bearing": "p_hub1.link1_seat"}))

    # 6x M6 Link 1 screws (Link 1 -> J1 Hub)
    for k, (x, y) in enumerate(pcd_points(45.0, 6, 0.0)):
        fid = f"f_l1_{k}"
        lib[fid] = load("ISO4762-M6x1.0-30")
        pl[fid] = {"R": I, "t_mm": [x, y, 70.0]} # head seats on link1 top; thread reaches hub tap through 20 mm link
        inst.append(TEMPLATES["screw_into_threaded_receiver"].bind({"screw": f"{fid}.thread", "receiver": f"p_hub1.link1_thread_{k+1}", "bearing": "p_link1.j1_top_face"}))

    # 4x M5 J1 pulley screws (through 72T pulley -> J1 hub underside)
    for k, (x, y) in enumerate(pcd_points(42.5, 4, 0.0)):
        fid = f"f_j1_p{k}"
        lib[fid] = load("ISO4762-M5x0.8-30")
        pl[fid] = {"R": R_flip, "t_mm": [x, y, -27.0]} # heads below pulley, threads up into hub
        inst.append(TEMPLATES["screw_into_threaded_receiver"].bind({"screw": f"{fid}.thread", "receiver": f"p_hub1.pulley_thread_{k+1}", "bearing": "p_pul72.mount_face"}))

    # 4x M6 base -> J1 motor bridge screws.
    for k, (x, y) in enumerate([(-60.0, -60.0), (-60.0, 60.0), (60.0, -60.0), (60.0, 60.0)]):
        fid = f"f_j1_mb{k}"
        lib[fid] = load("ISO4762-M6x1.0-30")
        pl[fid] = {"R": I, "t_mm": [x, y, 20.0]} # heads on base top; threads down into bridge
        inst.append(TEMPLATES["screw_into_threaded_receiver"].bind({"screw": f"{fid}.thread", "receiver": f"p_j1_mbridge.base_thread_{k+1}", "bearing": "p_base.top_face"}))

    # 4x M5 rear motor screws through NEMA23 body into the bridge.
    for k, (x, y) in enumerate([(-23.57, -23.57), (-23.57, 23.57), (23.57, -23.57), (23.57, 23.57)]):
        fid = f"f_m23_{k}"
        lib[fid] = load("ISO4762-M5x0.8-90")
        pl[fid] = {"R": R_flip, "t_mm": [D_j1 + x, y, -106.1]} # heads on rear face; threads up into bridge
        inst.append(TEMPLATES["screw_into_threaded_receiver"].bind({"screw": f"{fid}.thread", "receiver": f"p_j1_mbridge.motor_thread_{k+1}", "bearing": "p_motor23.back_face"}))

    # 8x M4 Outer J2 screws (Link 1 -> RU66 outer)
    # RU66 outer is inverted, mounted beneath Link 1. Outer ring bottom face is at Z=35, heading up to 50.
    for k, (x, y) in enumerate(pcd_points(41.5, 8, 22.5)):
        fid = f"f_j2_o{k}"
        lib[fid] = load("ULTRA_LOW_HEAD_M4x0.7-20")
        pl[fid] = {"R": R_flip, "t_mm": [300.0 + x, y, 35.0]} # Z=35 up to 55 (5 mm engagement)
        inst.append(TEMPLATES["screw_into_threaded_receiver"].bind({"screw": f"{fid}.thread", "receiver": f"p_link1.j2_thread_{k+1}", "bearing": "p_brg2.outer_ring_adapter_face"}))

    # 8x M4 Inner J2 screws (J2 Pulley -> RU66 inner)
    # Pulley bottom face is at Z=18, going up through pulley (17 mm) to bearing inner ring (Z=35).
    for k, (x, y) in enumerate(pcd_points(22.5, 8, 22.5)):
        fid = f"f_j2_i{k}"
        lib[fid] = load("ISO4762-M4x0.7-25")
        pl[fid] = {"R": R_flip, "t_mm": [300.0 + x, y, 18.0]} # Z=18 up to 43 (8 mm engagement)
        inst.append(TEMPLATES["screw_into_threaded_receiver"].bind({"screw": f"{fid}.thread", "receiver": f"p_brg2.inner_thread_{k+1}", "bearing": "p_pul60.link2_seat"}))

    # 6x M5 Link 2 screws (Link 2 -> J2 Pulley)
    # Link 2 bottom face is at Z=3, going up through Link 2 (15 mm) to custom pulley tapped holes (Z=18).
    for k, (x, y) in enumerate(pcd_points(35.0, 6, 0.0)):
        fid = f"f_l2_{k}"
        lib[fid] = load("ISO4762-M5x0.8-20")
        pl[fid] = {"R": R_flip, "t_mm": [300.0 + x, y, 3.0]} # Z=3 up to 23 (5 mm engagement)
        inst.append(TEMPLATES["screw_into_threaded_receiver"].bind({"screw": f"{fid}.thread", "receiver": f"p_pul60.link2_thread_{k+1}", "bearing": "p_link2.j2_bottom_face"}))

    # 4x M3 Link 1 -> J2 motor hanger screws.
    link_hanger_pts = [(-15.5, -15.5), (-15.5, 15.5), (15.5, -15.5), (15.5, 15.5)]
    for k, (dx, y) in enumerate(link_hanger_pts):
        fid = f"f_j2_h{k}"
        lib[fid] = load("ISO4762-M3x0.5-30")
        pl[fid] = {"R": I, "t_mm": [105.4 + dx, y, 70.0]} # head on Link 1 top, thread into hanger below
        inst.append(TEMPLATES["screw_into_threaded_receiver"].bind({"screw": f"{fid}.thread", "receiver": f"p_j2_mhanger.link_thread_{k+1}", "bearing": "p_link1.motor_bracket_top_face"}))

    # 4x M3 hanger -> NEMA17 face screws from the underside.
    motor_thread_pts = [(-15.5, -15.5), (-15.5, 15.5), (15.5, -15.5), (15.5, 15.5)]
    for k, (mx, my) in enumerate(motor_thread_pts):
        fid = f"f_m17_{k}"
        lib[fid] = load("ISO4762-M3x0.5-10")
        pl[fid] = {"R": R_flip, "t_mm": [105.4 + mx, M17_Y - my, 44.0]} # head under hanger, thread up into motor face
        inst.append(TEMPLATES["screw_into_threaded_receiver"].bind({"screw": f"{fid}.thread", "receiver": f"p_motor17.mount_thread_{k+1}", "bearing": "p_j2_mhanger.bottom_face"}))

    # 5. Evaluate Load Paths -- account for EVERY placed part. Belts are couplings
    #    (no load-bearing role) so they're declared non_structural; anything else placed
    #    but absent from the structural graph fails as UNACCOUNTED.
    NON_STRUCTURAL = {"p_belt_j1", "p_belt_j2"}
    rep = LP.evaluate(inst, lib, pl, ground=["p_base", "p_brg1"], mode="discovery",
                      placed=set(pl), non_structural=NON_STRUCTURAL)
    state = {r: ("UNHELD" if (b.state == LP.UNHELD or not b.accounted) else "HELD")
             for r, b in rep.bodies.items()}
    
    # 6. Format Assembly output JSON for visualizer
    asm = {"_axis": [0, 0, 1]}
    rend = []
    
    def get_name(ref):
        if ref == "p_belt_j1": return "Shoulder timing belt (S5M)"
        if ref == "p_belt_j2": return "Elbow timing belt (S5M)"
        if ref in lib:
            p = lib[ref]
            fam = p.classification.get("catalog_family", "").replace("_", " ")
            if "screw" in fam:
                d = p.normalized_parameters.get("thread_designation", "")
                l = p.normalized_parameters.get("nominal_length_mm", "")
                return f"{d.split('x')[0]}x{l} {fam}"
            if "custom_machined" in fam:
                return p.classification.get("aliases", [p.part_number])[0].replace("_", " ")
            if "pulley" in fam:
                return f"timing pulley ({p.part_number})"
            if "bearing" in fam:
                return f"cross roller bearing ({p.part_number})"
            return p.part_number
        return ref

    # Add components to visualizer
    render_configs = [
        ("p_base",      "/cad/BASE_INTERFACE_PLATE_REV_A.glb", 0x8a9097, -70),
        ("p_brg1_outer","/cad/RU85UUC0_outer.glb",             0xb5a642, -25),
        ("p_brg1_inner","/cad/RU85UUC0_inner.glb",             0xd4c14a, -25),
        ("p_hub1",      "/cad/J1_OUTPUT_HUB_REV_A.glb",        0xc0563f, 30),
        ("p_pul72",     "/cad/HTPA72S5M150.glb",               0x4a7fb0, 100),
        ("p_pul18_j1",  "/cad/HTPA18S5M150-A-H8.glb",          0x4ab07f, 100),
        ("p_j1_mbridge","/cad/J1_MOTOR_BRIDGE_REV_A.glb",      0x6f7a82, -40),
        ("p_motor23",   "/cad/iCL57-23.glb",                   0x9b59b6, -90),
        ("p_belt_j1",   "/cad/belt_s5m_j1.glb",                0x2b2f36, 100),
        
        ("p_link1",     "/cad/LINK_1_REV_A.glb",               0x90a8c2, 100),
        ("p_brg2_outer","/cad/RU66UUC0_outer.glb",             0xb5a642, -25),
        ("p_brg2_inner","/cad/RU66UUC0_inner.glb",             0xd4c14a, -25),
        ("p_pul60",     "/cad/J2_CUSTOM_PULLEY_REV_A.glb",     0xc0563f, 100),
        ("p_pul18_j2",  "/cad/HTPA18S5M150-A-H5.glb",          0x4ab07f, 100),
        ("p_j2_mhanger","/cad/J2_MOTOR_HANGER_REV_A.glb",       0x6f7a82, 70),
        ("p_motor17",   "/cad/iCL42-06.glb",                   0x9b59b6, -90),
        ("p_belt_j2",   "/cad/belt_s5m_j2.glb",                0x2b2f36, 100),
        
        ("p_link2",     "/cad/LINK_2_REV_A.glb",               0xd9c16a, 240),
    ]
    
    # Add fasteners dynamically
    for k in range(8):
        render_configs.append((f"f_j1_o{k}", "/cad/ISO4762-M5x0.8-25.glb", 0xe0e0e0, -45))
        render_configs.append((f"f_j1_i{k}", "/cad/ISO4762-M5x0.8-25.glb", 0xe0e0e0, 5))
    for k in range(6):
        render_configs.append((f"f_l1_{k}", "/cad/ISO4762-M6x1.0-30.glb", 0xe0e0e0, 100))
    for k in range(4):
        render_configs.append((f"f_j1_p{k}", "/cad/ISO4762-M5x0.8-30.glb", 0xe0e0e0, 100))
        render_configs.append((f"f_j1_mb{k}", "/cad/ISO4762-M6x1.0-30.glb", 0xe0e0e0, -25))
        render_configs.append((f"f_m23_{k}", "/cad/ISO4762-M5x0.8-90.glb", 0xe0e0e0, -100))
    for k in range(8):
        render_configs.append((f"f_j2_o{k}", "/cad/ULTRA_LOW_HEAD_M4x0.7-20.glb", 0xe0e0e0, 100))
        render_configs.append((f"f_j2_i{k}", "/cad/ISO4762-M4x0.7-25.glb", 0xe0e0e0, 100))
    for k in range(6):
        render_configs.append((f"f_l2_{k}", "/cad/ISO4762-M5x0.8-20.glb", 0xe0e0e0, 100))
    for k in range(4):
        render_configs.append((f"f_j2_h{k}", "/cad/ISO4762-M3x0.5-30.glb", 0xe0e0e0, 80))
        render_configs.append((f"f_m17_{k}", "/cad/ISO4762-M3x0.5-10.glb", 0xe0e0e0, 80))


    def base_ref(ref):
        # split bearing halves share the base bearing's pose/state/name
        for suf in ("_inner", "_outer"):
            if ref.endswith(suf) and (ref[:-len(suf)]) in pl:
                return ref[:-len(suf)]
        return ref

    for ref, url, col, ez in render_configs:
        pose = pl[base_ref(ref)]
        asm[ref] = {"R": pose["R"], "t_mm": [float(v) for v in pose["t_mm"]]}
        rend.append({
            "ref": ref,
            "url": url,
            "color": col,
            "explode": ez,
            "state": state.get(base_ref(ref), "HELD"),
            "name": get_name(base_ref(ref))
        })

    # Recognize the kinematic DOFs (revolute joints) and which parts move with each,
    # so the viewer can articulate them. Drive pulleys/motors are placed but not
    # structurally instanced -> pin them to their carrier via extra_fixed.
    from assembly.dof_extract import extract_dofs
    extra_fixed = {
        "p_pul72": "p_hub1",       # J1 output pulley turns with the hub
        "p_pul18_j1": "p_base",    # J1 motor pinion is on the stationary base
        "p_j1_mbridge": "p_base",
        "p_motor23": "p_base",
        "p_pul18_j2": "p_link1",   # J2 drive sits on link 1 (the J1 output frame)
        "p_j2_mhanger": "p_link1",
        "p_motor17": "p_link1",
        # A belt loop rides with the FRAME both its pulleys share (it can't rigidly
        # belong to either pulley). J1 belt spans base<->hub-axis => base frame (static);
        # J2 belt spans two pulleys both carried on link 1 => moves with link 1 (= J1).
        "p_belt_j1": "p_base",
        "p_belt_j2": "p_link1",
    }
    asm["_dofs"] = extract_dofs(inst, lib, pl, ground=["p_base"], extra_fixed=extra_fixed)
    for d in asm["_dofs"]:
        print(f"  DOF {d['id']}: {d['type']} axis={d['axis']} center={d['center']} "
              f"moves {len(d['moving'])} parts")

    asm["_render"] = rend
    # Embed the self-contained verification payload so this artifact is checkable by the
    # global gate (tools/verify_all.py) -- no assembly ships without its verification data.
    from assembly.verify_canonical import embed_verification
    embed_verification(asm, lib=lib, instances=inst, ground=["p_base", "p_brg1"],
                       placements=pl, non_structural=NON_STRUCTURAL)
    out_path = OUT / "two_joint_arm_assembly.json"
    out_path.write_text(json.dumps(asm, indent=2))
    print(f"\nWrote out/two_joint_arm_assembly.json -- {len(rend)} components")
    
    unacc = rep.unaccounted
    unheld = [r for r, b in rep.bodies.items()
              if r not in rep.ground and b.accounted and b.state == LP.UNHELD]
    if unacc:
        print(f"Gate: UNACCOUNTED (placed, no structural instance): {unacc}")
    if unheld:
        print(f"Gate: UNHELD: {unheld}")
    if not unacc and not unheld:
        print("Gate: ALL HELD")
    
    # Trigger camera render
    try:
        from tools.render import shoot
        imgs = shoot(str(OUT / "two_joint_arm_assembly.json"), str(OUT / "two_joint_arm"), "p_link2", ("iso", "z", "x"))
        print("Rendered:", ", ".join(imgs))
    except Exception as e:
        print(f"(render skipped: {e})")

if __name__ == "__main__":
    main()
