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

ROOT = Path(__file__).resolve().parent.parent
OUT, LIB = ROOT / "projects" / "rung3_rotary" / "out", ROOT / "library_v2"
I = [[1,0,0],[0,1,0],[0,0,1]]; R_XZ = [[0,0,-1],[0,1,0],[1,0,0]]
R_EXT = [[0,0,1],[0,1,0],[-1,0,0]]; R_EY = [[1,0,0],[0,0,1],[0,-1,0]]
D = 95.10
def load(s): return PartDefinition.from_json(json.loads((LIB/f"{s}.json").read_text()))
def pcd(r,n,start): return [(round(r*math.cos(math.radians(start+360/n*k)),2),
                            round(r*math.sin(math.radians(start+360/n*k)),2)) for k in range(n)]
SC5="/cad/ISO4762-M5x0.8-16.glb"; SC35="/cad/ISO4762-M5x0.8-35.glb"; M6="/cad/ISO4762-M6x1.0-16.glb"; TN="/cad/TNUT-M6-8mm.glb"

# ref -> (R, t_mm, url, color, explode_dz)
P = {
 "p_frX1":(R_EXT,[0,90,-35],"/cad/6575N203.glb",0x5f6a72,-130),
 "p_frX2":(R_EXT,[0,-90,-35],"/cad/6575N203.glb",0x5f6a72,-130),
 "p_frY1":(R_EY,[90,0,-35],"/cad/6575N203.glb",0x5f6a72,-130),
 "p_frY2":(R_EY,[-90,0,-35],"/cad/6575N203.glb",0x5f6a72,-130),
 "p_base":(I,[0,0,0],"/cad/ROTARY_BASE_RU85_REV_A.glb",0x8a9097,-70),
 "p_brg":(R_XZ,[0,0,0],"/cad/RU85UUC0.glb",0xb5a642,-25),
 "p_adp":(I,[0,0,15],"/cad/ROTARY_ADAPTER_RU85_S5M_REV_A.glb",0xc0563f,30),   # lower adapter
 "p_72":(R_XZ,[0,0,27],"/cad/HTPA72S5M150.glb",0x4a7fb0,100),                 # pulley on the pilot
 "p_belt":(I,[0,0,0],"/cad/belt_s5m.glb",0x2b2f36,100),
 "p_18":(R_XZ,[D,0,27],"/cad/HTPA18S5M150.glb",0x4ab07f,100),
 "p_motor":(I,[D,0,27],"/cad/NEMA23-MOTOR.glb",0x9b59b6,-90),
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
        "p_cap":"ROTARY_CAP_RU85_REV_A","p_top":"A6061FQM-200-200-10"}.items()}
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
    for ref,(R,t,url,col,ez) in P.items():
        asm[ref]={"R":R,"t_mm":[float(v) for v in t]}
        rend.append({"ref":ref,"url":url,"color":col,"explode":ez,"state":state.get(ref,"HELD")})
    asm["_render"]=rend
    (OUT/"rung3_assembly.json").write_text(json.dumps(asm, indent=2))
    held=[r for r,b in rep.bodies.items() if r not in rep.ground and b.state==LP.UNHELD]
    print(f"wrote out/rung3_assembly.json -- {len(rend)} parts incl. "
          f"{sum(1 for e in rend if 'ISO4762' in e['url'] or 'TNUT' in e['url'])} fasteners")
    print(f"gate: {'ALL HELD' if not held else 'UNHELD: '+str(held)}")
    for r,b in sorted(rep.bodies.items()):
        if r not in rep.ground: print(f"   {r}: {b.name}")


if __name__ == "__main__":
    main()
