"""THE canonical rung-3 assembly -> ONE file: out/rung3_assembly.json.

Single source of truth: every part (incl. fasteners, Hard Rule 6), its assembled pose,
an explode offset along Z, and its load-path gate state. VIEWS are query configs against
this one file in web/incr.html (?explode=, &hide=, &color=gate, &dir=). No per-view files.

ASSEMBLABLE 3-part rotating output (the trapped-pulley fix): lower adapter (REV_A) -> pulley
on its pilot -> BOLT-ON CAP on the pulley top (attaches at PCD85 inside the belt via 4 long
bolts cap->pulley->adapter; fans to +-55 above the belt) -> tabletop on the cap. Payload load
goes tabletop->cap->bolts->adapter (not through the pulley); nothing rotating sweeps the belt.
Build order has no traps: adapter->bearing, pulley on pilot, cap on pulley, bolts, tabletop.
"""
from __future__ import annotations
import json, math
from pathlib import Path
from ontology.schema_v2 import PartDefinition
from ontology.templates import TEMPLATES
from ontology import load_path as LP
from assembly.verify import verify_assembly
from assembly.verify_canonical import embed_verification
import benchmarks.rung3_interference as I3

ROOT = Path(__file__).resolve().parent.parent
OUT, LIB = ROOT / "projects" / "rung3_rotary" / "out", ROOT / "library_v2"
I = [[1,0,0],[0,1,0],[0,0,1]]; R_XZ = [[0,0,-1],[0,1,0],[1,0,0]]
R_EXT = [[0,0,1],[0,1,0],[-1,0,0]]; R_EY = [[1,0,0],[0,0,1],[0,-1,0]]
D = 148.74   # 4:1 belt center distance, stepped OUT from 95.1 so the NEMA23 body clears the
             # x=110 machine footprint (10.5 mm margin). Belt regenerated to 107T S5M to suit.
def load(s): return PartDefinition.from_json(json.loads((LIB/f"{s}.json").read_text()))
def pcd(r,n,start): return [(round(r*math.cos(math.radians(start+360/n*k)),2),
                            round(r*math.sin(math.radians(start+360/n*k)),2)) for k in range(n)]
SC5="/cad/ISO4762-M5x0.8-16.glb"; SC35="/cad/ISO4762-M5x0.8-35.glb"; M6="/cad/ISO4762-M6x1.0-16.glb"; TN="/cad/TNUT-M6-8mm.glb"

# ref -> (R, t_mm, url, color, explode_dz)
P = {
 # butt-jointed frame, 6575N203 profile CUT to length (build_frame.py): X-rails run full and
 # EXTENDED in +X (x[-110,180], centered x=35) so the motor bay reaches the outboard NEMA23;
 # Y-rails seat BETWEEN them (y+-70) at x=+-90. Members BUTT (touch) -- no corner interpenetration;
 # rails stay on the +-90 lines so all 8 base anchors land on steel.
 "p_frX1":(R_EXT,[35,90,-35],"/cad/frame_railX_290.glb",0x5f6a72,-130),
 "p_frX2":(R_EXT,[35,-90,-35],"/cad/frame_railX_290.glb",0x5f6a72,-130),
 "p_frY1":(R_EY,[90,0,-35],"/cad/frame_railY_140.glb",0x5f6a72,-130),
 "p_frY2":(R_EY,[-90,0,-35],"/cad/frame_railY_140.glb",0x5f6a72,-130),
 "p_mmount":(I,[0,0,0],"/cad/MOTOR_MOUNT_RU85_REV_A.glb",0x6f7a82,-150),         # bridge: X-rails -> NEMA23 face at z27
 "p_base":(I,[0,0,0],"/cad/ROTARY_BASE_RU85_REV_A.glb",0x8a9097,-70),
 "p_brg":(R_XZ,[0,0,0],"/cad/RU85UUC0.glb",0xb5a642,-25),
 "p_adp":(I,[0,0,15],"/cad/ROTARY_ADAPTER_RU85_S5M_REV_A.glb",0xc0563f,30),   # lower adapter
 "p_72":(R_XZ,[0,0,27],"/cad/HTPA72S5M150.glb",0x4a7fb0,100),                 # pulley on the pilot
 "p_belt":(I,[0,0,0],"/cad/belt_s5m.glb",0x2b2f36,100),
 "p_18":(R_XZ,[D,0,27],"/cad/HTPA18S5M150.glb",0x4ab07f,100),
 "p_motor":(I,[D,0,0.4],"/cad/NEMA23-MOTOR.glb",0x9b59b6,-90),   # face on the bridge underside (z23), shaft up to the 18T
 "p_cap":(I,[0,0,49],"/cad/ROTARY_CAP_RU85_REV_A.glb",0xcf8a7a,165),          # bolt-on cap on the pulley top
 "p_top":(I,[0,0,59],"/cad/A6061-tabletop.glb",0xd9c16a,240),                 # tabletop on the cap
}
for k,(x,y) in enumerate(pcd(42.5,4,0)):   P[f"fcap{k}"]=(I,[x,y,54],SC35,0xe0e0e0,165)  # 4 M5x35: cap->pulley->adapter, head recessed in cap (Z54)
for k,(x,y) in enumerate(pcd(32.5,8,22.5)):P[f"fi{k}"]=(I,[x,y,27],SC5,0xe0e0e0,5)       # 8 adapter->inner ring
for k,(x,y) in enumerate(pcd(52.5,8,22.5)):P[f"fo{k}"]=(I,[x,y,9],SC5,0xe0e0e0,-45)      # 8 base->outer ring
for k,(x,y) in enumerate([(55,55),(-55,55),(-55,-55),(55,-55)]): P[f"ft{k}"]=(I,[float(x),float(y),62.5],M6,0xe0e0e0,240)  # 4 tabletop->cap (head recessed in tabletop)
ANC=[(-60,90),(60,90),(-60,-90),(60,-90),(90,-60),(90,60),(-90,-60),(-90,60)]
for k,(x,y) in enumerate(ANC): P[f"fa{k}"]=(I,[float(x),float(y),-6.5],M6,0xe0e0e0,-100)
for k,(x,y) in enumerate(ANC): P[f"tn{k}"]=(I,[float(x),float(y),-20.5],TN,0xcc8844,-120)


def main():
    lib={r:load(s) for r,s in {"p_base":"ROTARY_BASE_RU85_REV_A","p_brg":"RU85UUC0",
        "p_adp":"ROTARY_ADAPTER_RU85_S5M_REV_A","p_72":"HTPA72S5M150-A-H50-KFC85-K5.5",
        "p_cap":"ROTARY_CAP_RU85_REV_A","p_top":"A6061FQM-200-200-10",
        "p_mmount":"MOTOR_MOUNT_RU85_REV_A"}.items()}   # bracket in lib so cad_fidelity covers it
    pl={r:{"R":P[r][0],"t_mm":P[r][1]} for r in lib}
    inst=[
      TEMPLATES["bearing_ring_mount"].bind({"plate":"p_adp.inner_race_boss","ring":"p_brg.inner_ring_adapter_face",
        "forbidden":"p_brg.outer_ring_adapter_face","plate_group":"p_adp:inner_race_pattern","ring_group":"p_brg:inner_ring_pattern"}),
      TEMPLATES["pilot_located_bolted_hub"].bind({"hub":"p_72.bore","pilot":"p_adp.pulley_pilot",
        "hub_seat":"p_72.mount_face","seat":"p_adp.pulley_seat","hub_group":"p_72:mount_pattern","seat_group":"p_adp:pulley_pattern"}),
      # cap clamped to the adapter by the 4 PCD85 long bolts SPANNING the pulley (axial offset)
      TEMPLATES["through_bolted_plate"].bind({"plate":"p_cap.bot_face","receiver":"p_adp.pulley_seat",
        "plate_group":"p_cap:mount_pattern","receiver_group":"p_adp:pulley_pattern"}),
      TEMPLATES["bounded_bolt_pattern_seat"].bind({"plate":"p_top.bot_face","seat":"p_cap.top_face",
        "plate_group":"p_top:mount_pattern","seat_group":"p_cap:tabletop_pattern"}),
    ]
    for k in range(8):
        lib[f"fi{k}"]=load("ISO4762-M5x0.8-16"); pl[f"fi{k}"]={"R":I,"t_mm":P[f"fi{k}"][1]}
        inst.append(TEMPLATES["screw_into_threaded_receiver"].bind({"screw":f"fi{k}.thread","receiver":f"p_brg.inner_thread_{k+1}"}))
    for k in range(4):  # the 4 long bolts: count for BOTH the pulley mount and the cap mount (shared, into the adapter)
        lib[f"fcap{k}"]=load("ISO4762-M5x0.8-35"); pl[f"fcap{k}"]={"R":I,"t_mm":P[f"fcap{k}"][1]}
        inst.append(TEMPLATES["screw_into_threaded_receiver"].bind({"screw":f"fcap{k}.thread","receiver":f"p_adp.pulley_thread_{k+1}"}))
    for k in range(4):  # 4 M6: tabletop -> cap
        lib[f"ft{k}"]=load("ISO4762-M6x1.0-16"); pl[f"ft{k}"]={"R":I,"t_mm":P[f"ft{k}"][1]}
        inst.append(TEMPLATES["screw_into_threaded_receiver"].bind({"screw":f"ft{k}.thread","receiver":f"p_cap.tabletop_thread_{k+1}"}))
    rep=LP.evaluate(inst, lib, pl, ground=["p_base","p_brg"], mode="discovery")
    state={r:("UNHELD" if b.state==LP.UNHELD else "HELD") for r,b in rep.bodies.items()}
    asm={"_axis":[0,0,1]}; rend=[]
    
    def get_name(ref, url):
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
        b = Path(url).stem
        if "ISO4762" in b:
            pts = b.split("-")
            return f"{pts[1].split('x')[0]}x{pts[2]} socket head cap screw" if len(pts)>2 else b
        if "TNUT" in b: return "M6 T-slot nut"
        if "6575N203" in b: return "40x40 extrusion"
        if "NEMA23" in b: return "NEMA23 stepper motor"
        if "belt" in b: return "S5M timing belt"
        return b

    for ref,(R,t,url,col,ez) in P.items():
        asm[ref]={"R":R,"t_mm":[float(v) for v in t]}
        rend.append({"ref":ref,"url":url,"color":col,"explode":ez,"state":state.get(ref,"HELD"),"name":get_name(ref, url)})
    asm["_render"]=rend
    embed_verification(asm, lib=lib, instances=inst, ground=["p_base", "p_brg"], placements=pl)
    (OUT/"rung3_assembly.json").write_text(json.dumps(asm, indent=2))
    print(f"wrote out/rung3_assembly.json -- {len(rend)} parts incl. "
          f"{sum(1 for e in rend if 'ISO4762' in e['url'] or 'TNUT' in e['url'])} fasteners")
    # The MAIN verification set -- load_path + cad_fidelity + interference -- via the shared
    # harness every rung uses (assembly/verify.py), so the gates stay identical across rungs.
    verify_assembly("rung3", {r: asm[r] for r in P}, {r: P[r][2] for r in P},
                    lib=lib, instances=inst, ground=["p_base", "p_brg"],
                    designed=I3.designed, rotating=I3.rotating)
    for r,b in sorted(rep.bodies.items()):
        if r not in rep.ground: print(f"   {r}: {b.name}")


if __name__ == "__main__":
    main()
