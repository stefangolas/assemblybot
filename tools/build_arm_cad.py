import os
import math
import cadquery as cq
import cascadio

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAD = os.path.join(ROOT, "cad")
os.makedirs(CAD, exist_ok=True)

# Tap-drill diameters for the minor thread representation
TAP = {"M3": 2.50, "M4": 3.30, "M5": 4.20, "M6": 5.00}

def _cyl(d, z0, z1, x=0.0, y=0.0):
    """A cutter cylinder of diameter d spanning z0..z1, centered at (x,y)."""
    return (cq.Workplane("XY").workplane(offset=z0).center(x, y)
            .circle(d / 2.0).extrude(z1 - z0))

def emit(part, name):
    stp = os.path.join(CAD, name + ".step")
    glb = os.path.join(CAD, name + ".glb")
    cq.exporters.export(part, stp)
    cascadio.step_to_glb(stp, glb)
    print(f"Generated {name}: STEP -> {stp}, GLB -> {glb}")

def pcd_points(r, n=8, start=22.5):
    """Compute points on a PCD circle."""
    pts = []
    for k in range(n):
        ang = math.radians(start + (360.0 / n) * k)
        pts.append((r * math.cos(ang), r * math.sin(ang)))
    return pts

# ============================================================================
# 1. RU66 bearing (RU66UUC0)
# ============================================================================
def build_ru66():
    # ID=35, OD=95, Width=15. Outer ring annulus 55..95, Inner ring annulus 35..47
    brg = (cq.Workplane("XY").circle(95.0 / 2.0).extrude(15.0)
           .cut(cq.Workplane("XY").circle(35.0 / 2.0).extrude(15.0)))
    
    # 8x M4 tapped through PCD45 on the inner ring (we'll make PCD at 22.5 deg)
    for (x, y) in pcd_points(45.0 / 2.0, 8, 22.5):
        brg = brg.cut(_cyl(TAP["M4"], -1.0, 16.0, x, y))
        
    # 8x Oe4.5 clearance through PCD83 on the outer ring (at 22.5 deg)
    for (x, y) in pcd_points(83.0 / 2.0, 8, 22.5):
        brg = brg.cut(_cyl(4.5, -1.0, 16.0, x, y))
        
    # Visual race separation groove: split the outer/inner rings at R=25.5..26.5, depth 1.0 on both faces
    brg = brg.cut(cq.Workplane("XY").workplane(offset=0.0).circle(53.0 / 2.0).rect(2.0, 2.0).extrude(1.0))
    brg = brg.cut(cq.Workplane("XY").workplane(offset=14.0).circle(53.0 / 2.0).rect(2.0, 2.0).extrude(1.0))
    return brg

# ============================================================================
# 2. NEMA 17 Motor (iCL42-06)
# ============================================================================
def build_nema17():
    # Body 42 x 42 x 40
    m = cq.Workplane("XY").box(42.0, 42.0, 40.0, centered=(True, True, False))
    # Pilot boss Ø22 x 2
    m = m.union(cq.Workplane("XY").workplane(offset=40.0).circle(22.0 / 2.0).extrude(2.0))
    # Shaft Ø5 x 24 (extends from boss top)
    m = m.union(cq.Workplane("XY").workplane(offset=42.0).circle(5.0 / 2.0).extrude(24.0))
    # 4x M3 tapped holes depth 4.5 on 31 x 31 square
    for x in [-15.5, 15.5]:
        for y in [-15.5, 15.5]:
            m = m.cut(_cyl(TAP["M3"], 35.5, 41.0, x, y))
    return m

# ============================================================================
# 3. NEMA 23 Motor (iCL57-23)
# ============================================================================
def build_nema23():
    # Body 57 x 57 x 80
    m = cq.Workplane("XY").box(57.0, 57.0, 80.0, centered=(True, True, False))
    # Pilot boss Ø38.1 x 1.6
    m = m.union(cq.Workplane("XY").workplane(offset=80.0).circle(38.1 / 2.0).extrude(1.6))
    # Shaft Ø8 x 21
    m = m.union(cq.Workplane("XY").workplane(offset=81.6).circle(8.0 / 2.0).extrude(21.0))
    # 4x Ø5.0 through clearance holes on 47.14 x 47.14 square
    for x in [-23.57, 23.57]:
        for y in [-23.57, 23.57]:
            m = m.cut(_cyl(5.0, -1.0, 82.0, x, y))
    return m

# ============================================================================
# 4. 18T S5M Pulley (HTPA18S5M150-A-H5)
# ============================================================================
def build_pulley18(bore_mm=5.0):
    # Pitch dia = 28.65, OD = 27.5. Width 15 teeth section, overall 22.
    p = cq.Workplane("XY").circle(27.5 / 2.0).extrude(15.0)
    # Flange or boss Ø22 x 7
    p = p.union(cq.Workplane("XY").workplane(offset=15.0).circle(22.0 / 2.0).extrude(7.0))
    # Shaft bore through
    p = p.cut(_cyl(bore_mm, -1.0, 23.0))
    return p

# ============================================================================
# 5. Base Interface Plate (BASE_INTERFACE_PLATE_REV_A)
# ============================================================================
def build_base():
    # Round disc Ø180 x 20
    b = cq.Workplane("XY").circle(180.0 / 2.0).extrude(20.0)
    # Central relief opening Ø94
    b = b.cut(_cyl(94.0, -1.0, 22.0))
    # 8x M5 tapped holes on PCD105 @ 22.5 deg (outer ring interface)
    for (x, y) in pcd_points(105.0 / 2.0, 8, 22.5):
        b = b.cut(_cyl(TAP["M5"], -1.0, 21.0, x, y))
    # 4x Ø6.6 through holes on 120 x 120 square (inside the Ø180 disk)
    for x in [-60.0, 60.0]:
        for y in [-60.0, 60.0]:
            b = b.cut(_cyl(6.6, -1.0, 21.0, x, y))
    return b

# ============================================================================
# 6. J1 Output Hub (J1_OUTPUT_HUB_REV_A)
# ============================================================================
def build_hub1():
    # Drive shaft Ø30 x 40 extending Z=0..40
    h = cq.Workplane("XY").circle(30.0 / 2.0).extrude(40.0)
    # Lower pilot boss for the J1 72T pulley: Ø50 through the full pulley bore,
    # plus a compact Ø92 tapped flange that stays inside the base plate Ø94 relief.
    h = h.union(_cyl(50.0, -22.0, 0.0))
    h = h.union(_cyl(92.0, 0.0, 8.0))
    # Inner-ring contact land: Ø76 x 5 (Z=40..45)
    h = h.union(_cyl(76.0, 40.0, 45.0))
    # Upper flange: Ø110 x 10 (Z=45..55)
    h = h.union(_cyl(110.0, 45.0, 55.0))
    
    # Relieve the underside of the flange outside the contact land by 0.5 mm (Z=45 to Z=45.5, R=38..55)
    # We do this by cutting an annular cylinder
    h = h.cut(cq.Workplane("XY").workplane(offset=45.0).circle(111.0 / 2.0).extrude(0.5)
              .cut(cq.Workplane("XY").workplane(offset=44.0).circle(76.0 / 2.0).extrude(3.0)))
              
    # Bearing fasteners: 8x Ø5.5 clearance holes on PCD65
    for (x, y) in pcd_points(65.0 / 2.0, 8, 22.5):
        h = h.cut(_cyl(5.5, 39.0, 56.0, x, y))

    # Driven pulley attachment: 4x M5 tapped blind holes on PCD85 from the underside.
    for (x, y) in pcd_points(85.0 / 2.0, 4, 0.0):
        h = h.cut(_cyl(TAP["M5"], -1.0, 9.0, x, y))
        
    # Link 1 attachment: 6x M6 tapped holes on PCD90 @ 60 deg increments (start 0)
    for (x, y) in pcd_points(90.0 / 2.0, 6, 0.0):
        h = h.cut(_cyl(TAP["M6"], 43.0, 56.0, x, y)) # depth 12 blind from top
        
    # 2x Ø6 dowel pin holes on PCD90 at 90 and 270 deg
    for (x, y) in [(0, 45.0), (0, -45.0)]:
        h = h.cut(_cyl(6.0, 40.0, 56.0, x, y))
        
    return h

# ============================================================================
# 7. Link 1 (LINK_1_REV_A)
# ============================================================================
def build_link1():
    # Link thickness 20 mm (Z=0..20)
    # Lobe 1 centered at (0,0) - radius 60
    # Lobe 2 centered at (300,0) - radius 55
    # Connect with a box of width 90
    l1 = (cq.Workplane("XY").circle(60.0).extrude(20.0)
          .union(cq.Workplane("XY").workplane(offset=0.0).center(300.0, 0.0).circle(55.0).extrude(20.0))
          .union(cq.Workplane("XY").center(150.0, 0.0).box(300.0, 90.0, 20.0, centered=(True, True, False))))
          
    # Proximal end (J1 interface):
    # Central hole Ø45
    l1 = l1.cut(_cyl(45.0, -1.0, 22.0))
    # 6x Ø6.6 clearance holes on PCD90
    for (x, y) in pcd_points(90.0 / 2.0, 6, 0.0):
        l1 = l1.cut(_cyl(6.6, -1.0, 22.0, x, y))
    # 2x Ø6 dowel holes on PCD90 (at y=45, y=-45)
    for (x, y) in [(0.0, 45.0), (0.0, -45.0)]:
        l1 = l1.cut(_cyl(6.0, -1.0, 22.0, x, y))
        
    # Distal end (J2 bearing interface):
    # Central relief Ø75
    l1 = l1.cut(_cyl(75.0, -1.0, 22.0, 300.0, 0.0))
    # 8x M4 tapped holes on PCD83 @ 22.5 deg (relative to elbow center)
    for (x, y) in pcd_points(83.0 / 2.0, 8, 22.5):
        l1 = l1.cut(_cyl(TAP["M4"], -1.0, 22.0, 300.0 + x, y))
        
    # Elbow motor plate mounting slots (NEMA 17):
    # Center of slots at X = 105.4, Y = 0
    # Central pilot clearance Ø23
    l1 = l1.cut(_cyl(23.0, -1.0, 22.0, 105.4, 0.0))
    # 4x slots for M3 screws on a 31 x 31 mm pattern, slots run parallel to X axis (+-6 mm)
    for dx in [-15.5, 15.5]:
        for dy in [-15.5, 15.5]:
            l1 = l1.cut(cq.Workplane("XY").workplane(offset=-1.0).center(105.4 + dx, dy)
                        .box(12.0, 3.2, 22.0, centered=(True, True, False)))
                        
    return l1

# ============================================================================
# 8. J2 Custom Pulley/Flange (J2_CUSTOM_PULLEY_REV_A)
# ============================================================================
def build_pulley2():
    # 60T S5M Pulley body: Ø94.3 x 15 (Z=0..15)
    p2 = cq.Workplane("XY").circle(94.3 / 2.0).extrude(15.0)
    # Upper contact land: Ø58 x 2 (Z=15..17)
    p2 = p2.union(_cyl(58.0, 15.0, 17.0))
    # Central bore Ø30
    p2 = p2.cut(_cyl(30.0, -1.0, 18.0))
    
    # 8x Ø4.5 clearance holes on PCD45
    for (x, y) in pcd_points(45.0 / 2.0, 8, 22.5):
        p2 = p2.cut(_cyl(4.5, -1.0, 18.0, x, y))
        
    # Lower face pilot register recess: Ø70 x 2 deep (Z=0..2)
    p2 = p2.cut(_cyl(70.0, 0.0, 2.0))
    
    # Lower face link mounting: 6x M5 tapped holes on PCD70
    for (x, y) in pcd_points(70.0 / 2.0, 6, 0.0):
        p2 = p2.cut(_cyl(TAP["M5"], -1.0, 10.0, x, y)) # Z=0..10
        
    # 2x Ø6 dowel holes on PCD70 (at 90 and 270 deg)
    for (x, y) in [(0.0, 35.0), (0.0, -35.0)]:
        p2 = p2.cut(_cyl(6.0, -1.0, 10.0, x, y))
        
    return p2

# ============================================================================
# 9. Link 2 (LINK_2_REV_A)
# ============================================================================
def build_link2():
    # Link thickness 15 mm (Z=0..15)
    # Lobe 1 centered at (0,0) - radius 45 (for J2 interface)
    # Distal end: box flange 60 x 60 centered at (300,0)
    # Connect with a box of width 75
    l2 = (cq.Workplane("XY").circle(45.0).extrude(15.0)
          .union(cq.Workplane("XY").workplane(offset=0.0).center(300.0, 0.0).box(60.0, 60.0, 15.0, centered=(True, True, False)))
          .union(cq.Workplane("XY").center(150.0, 0.0).box(300.0, 75.0, 15.0, centered=(True, True, False))))
          
    # Proximal interface:
    # Central pilot register boss: Ø70 x 2 (Z=15..17)
    l2 = l2.union(_cyl(70.0, 15.0, 17.0))
    # Clearance hole Ø30 (cabling)
    l2 = l2.cut(_cyl(30.0, -1.0, 18.0))
    # 6x Ø5.5 clearance holes on PCD70
    for (x, y) in pcd_points(70.0 / 2.0, 6, 0.0):
        l2 = l2.cut(_cyl(5.5, -1.0, 18.0, x, y))
    # 2x Ø6 dowel holes on PCD70 (at y=35, y=-35)
    for (x, y) in [(0.0, 35.0), (0.0, -35.0)]:
        l2 = l2.cut(_cyl(6.0, -1.0, 18.0, x, y))
        
    # Tool interface at distal end:
    # Central pass-through Ø25
    l2 = l2.cut(_cyl(25.0, -1.0, 16.0, 300.0, 0.0))
    # 4x M5 tapped holes on a 40 x 40 mm square grid
    for dx in [-20.0, 20.0]:
        for dy in [-20.0, 20.0]:
            l2 = l2.cut(_cyl(TAP["M5"], -1.0, 12.0, 300.0 + dx, dy)) # depth 12
    # 2x Ø5 dowel holes (at X=300+25, Y=0 and X=300-25, Y=0)
    for (dx, dy) in [(25.0, 0.0), (-25.0, 0.0)]:
        l2 = l2.cut(_cyl(5.0, -1.0, 16.0, 300.0 + dx, dy))
        
    return l2

def build_j2_motor_hanger():
    plate = cq.Workplane("XY").center(0.0, 35.0).box(90.0, 140.0, 6.0, centered=(True, True, False))
    # Motor pilot clearance plus four M3 clearance holes at the outboard motor face.
    plate = plate.cut(_cyl(23.0, -1.0, 7.0, 0.0, 0.0))
    for x, y in [(-15.5, 15.5), (-15.5, -15.5), (15.5, 15.5), (15.5, -15.5)]:
        plate = plate.cut(_cyl(3.4, -1.0, 7.0, x, y))
    # Four M3 tapped holes that pick up the existing Link 1 NEMA17 slot pattern.
    for x, y in [(-15.5, 59.5), (-15.5, 90.5), (15.5, 59.5), (15.5, 90.5)]:
        plate = plate.cut(_cyl(TAP["M3"], -1.0, 7.0, x, y))
    return plate

def build_j1_motor_bridge():
    bridge_height = 26.1
    hub_clearance_x = -95.314
    motor_plate = cq.Workplane("XY").workplane(offset=-6.0).box(72.0, 72.0, 6.0, centered=(True, True, False))
    motor_plate = motor_plate.cut(_cyl(56.0, -7.0, 1.0))

    top_plate = cq.Workplane("XY").workplane(offset=bridge_height - 6.0).center(-62.5, 0.0).box(215.0, 144.0, 6.0, centered=(True, True, False))

    side_walls = cq.Workplane("XY")
    for y in [-82.0, 82.0]:
        side_walls = side_walls.union(cq.Workplane("XY").workplane(offset=-6.0).center(-62.5, y).box(215.0, 8.0, bridge_height + 6.0, centered=(True, True, False)))
    lower_arms = cq.Workplane("XY")
    for y in [-60.0, 60.0]:
        lower_arms = lower_arms.union(cq.Workplane("XY").workplane(offset=-6.0).center(-2.5, y).box(75.0, 48.0, 6.0, centered=(True, True, False)))
    bridge = motor_plate.union(top_plate).union(side_walls).union(lower_arms)
    for x, y in [(-23.57, -23.57), (-23.57, 23.57), (23.57, -23.57), (23.57, 23.57)]:
        bridge = bridge.cut(_cyl(TAP["M5"], -7.0, 1.0, x, y))
    for x, y in [(-155.314, -60.0), (-155.314, 60.0), (-35.314, -60.0), (-35.314, 60.0)]:
        bridge = bridge.cut(_cyl(TAP["M6"], bridge_height - 6.1, bridge_height + 1.0, x, y))
    # The bridge origin is the motor shaft; the J1 output axis sits at local X=-95.314.
    # Keep the fixed bridge clear of the rotating hub flange, 72T pulley, and belt stack.
    bridge = bridge.cut(_cyl(140.0, -7.0, bridge_height + 1.0, hub_clearance_x, 0.0))
    return bridge

def build_screw(d_shank, l_shank, d_head, h_head):
    # Head at Z=0..h_head, Shank at Z=-l_shank..0
    head = cq.Workplane("XY").circle(d_head / 2.0).extrude(h_head)
    shank = cq.Workplane("XY").workplane(offset=-l_shank).circle(d_shank / 2.0).extrude(l_shank)
    return head.union(shank)

def build_set_screw(d_shank, l_shank):
    return cq.Workplane("XY").circle(d_shank / 2.0).extrude(l_shank)

def main():
    emit(build_ru66().rotate((0, 0, 0), (0, 1, 0), 90), "RU66UUC0")
    emit(build_nema17(), "iCL42-06")
    emit(build_nema23(), "iCL57-23")
    emit(build_pulley18(5.0).rotate((0, 0, 0), (0, 1, 0), 90), "HTPA18S5M150-A-H5")
    emit(build_pulley18(8.0).rotate((0, 0, 0), (0, 1, 0), 90), "HTPA18S5M150-A-H8")
    emit(build_base(), "BASE_INTERFACE_PLATE_REV_A")
    emit(build_hub1(), "J1_OUTPUT_HUB_REV_A")
    emit(build_link1(), "LINK_1_REV_A")
    emit(build_pulley2(), "J2_CUSTOM_PULLEY_REV_A")
    emit(build_link2(), "LINK_2_REV_A")
    emit(build_j2_motor_hanger(), "J2_MOTOR_HANGER_REV_A")
    emit(build_j1_motor_bridge(), "J1_MOTOR_BRIDGE_REV_A")
    # Screws
    emit(build_set_screw(4.0, 6.0), "DIN913-M4x0.7-6")
    emit(build_screw(3.0, 10.0, 5.5, 3.0), "ISO4762-M3x0.5-10")
    emit(build_screw(3.0, 30.0, 5.5, 3.0), "ISO4762-M3x0.5-30")
    emit(build_screw(4.0, 20.0, 7.0, 2.0), "ULTRA_LOW_HEAD_M4x0.7-20")
    emit(build_screw(4.0, 20.0, 7.0, 4.0), "ISO4762-M4x0.7-20")
    emit(build_screw(4.0, 25.0, 7.0, 4.0), "ISO4762-M4x0.7-25")
    emit(build_screw(5.0, 20.0, 8.5, 5.0), "ISO4762-M5x0.8-20")
    emit(build_screw(5.0, 25.0, 8.5, 5.0), "ISO4762-M5x0.8-25")
    emit(build_screw(5.0, 30.0, 8.5, 5.0), "ISO4762-M5x0.8-30")
    emit(build_screw(5.0, 90.0, 8.5, 5.0), "ISO4762-M5x0.8-90")
    emit(build_screw(6.0, 30.0, 10.0, 6.0), "ISO4762-M6x1.0-30")
    print("All CAD models successfully generated.")

if __name__ == "__main__":
    main()
