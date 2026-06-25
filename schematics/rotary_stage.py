"""Rung-3 rotary stage -- parametric SCHEMATIC (mm). One params dict; the cross-section
(cutaway) is built from it. Colors match the 3D render so parts map 1:1. This is a
design-review schematic: envelopes parameter-driven, internals simplified.
"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from schematics import primitives as P

# --- world Z (mm), from the assembly: stack bottom->top ---
S = dict(
  frame=dict(x=(70,110), z=(-55,-15)),
  base=dict(r=(47,110), z=(-15,0)),
  brg_out=dict(r=(46.5,60), z=(0,15)), brg_in=dict(r=(27.5,38.5), z=(0,15)), roller_r=43,
  adapter=dict(r=(22.5,90), z=(15,27)), pilot=dict(r=(22.5,25), z=(27,30)),
  pulley=dict(r=(25,59.5), z=(27,49)),
  cap=dict(r=(22.5,90), z=(49,59)),
  tabletop=dict(hw=100, z=(59,69)),
  passthrough_r=22.5,
  cap_bolt=dict(r=42.5, head_top=59, length=40, dia=5, head_dia=9, head_h=5),   # M5x35: cap->pulley->ADAPTER
  inner_bolt=dict(r=32.5, head_top=27, length=21, dia=5, head_dia=9.5, head_h=5),# M5x16: adapter->bearing inner
  table_bolt=dict(r=77.8, head_top=69, length=22, dia=6, head_dia=11, head_h=6), # M6x16: tabletop->cap
)
COL = dict(adapter="#c0563f", pulley="#4a7fb0", cap="#cf8a7a", tabletop="#d9c16a", bearing="#b5a642")

def cutaway(path="out/rung3_cutaway.png"):
    fig, ax = plt.subplots(figsize=(12, 9))
    fr=S["frame"]; P.block(ax,-fr["x"][1],-fr["x"][0],*fr["z"],group="stationary"); P.block(ax,*fr["x"],*fr["z"],group="stationary")
    P.ring(ax,*S["base"]["r"],*S["base"]["z"],group="stationary")
    P.ring(ax,*S["brg_out"]["r"],*S["brg_out"]["z"],group="stationary",facecolor=COL["bearing"],hatch="")
    P.ring(ax,*S["brg_in"]["r"],*S["brg_in"]["z"],group="rotating",facecolor=COL["bearing"])
    P.crossed_rollers(ax,S["roller_r"],7.5)
    P.ring(ax,*S["adapter"]["r"],*S["adapter"]["z"],group="rotating",facecolor=COL["adapter"])
    P.ring(ax,*S["pilot"]["r"],*S["pilot"]["z"],group="rotating",facecolor=COL["adapter"])
    P.ring(ax,*S["pulley"]["r"],*S["pulley"]["z"],group="pulley",facecolor=COL["pulley"])
    P.ring(ax,*S["cap"]["r"],*S["cap"]["z"],group="rotating",facecolor=COL["cap"])
    P.bar(ax,S["tabletop"]["hw"],*S["tabletop"]["z"],group="payload",facecolor=COL["tabletop"])
    # fasteners (the join is the point)
    cb=S["cap_bolt"];   P.bolt(ax,cb["r"],cb["head_top"],cb["length"],cb["dia"],cb["head_dia"],cb["head_h"])
    ib=S["inner_bolt"]; P.bolt(ax,ib["r"],ib["head_top"],ib["length"],ib["dia"],ib["head_dia"],ib["head_h"])
    tb=S["table_bolt"]; P.bolt(ax,tb["r"],tb["head_top"],tb["length"],tb["dia"],tb["head_dia"],tb["head_h"])
    P.passthrough(ax,S["passthrough_r"],-15,69); P.centerline(ax,-60,72)
    # callouts
    ax.annotate("4x M5x35 CAP BOLT\n cap -> (through) pulley -> ADAPTER\n = the cap-to-base join\n (head recessed in cap)",
                xy=(-42.5,38),xytext=(-345,40),fontsize=11,fontweight="bold",color="#0a0c0f",va="center",
                arrowprops=dict(arrowstyle="->",lw=1.6))
    ax.annotate("8x M5x16: adapter -> bearing INNER ring",xy=(-32.5,10),xytext=(-345,6),fontsize=10,va="center",arrowprops=dict(arrowstyle="->"))
    ax.annotate("4x M6x16: tabletop -> cap",xy=(-77.8,63),xytext=(-345,69),fontsize=10,va="center",arrowprops=dict(arrowstyle="->"))
    for z,t in [(-35,"40mm T-slot FRAME (fixed)"),(-8,"BASE (fixed) -> 8x M6/T-nuts to frame"),
                (7,"RU85 BEARING = joint (outer fixed | inner ROTATES)"),(21,"ADAPTER (rotates, 'orange base')"),
                (38,"72T PULLEY (torque only)"),(54,"CAP (pink)"),(64,"~200mm TABLETOP (payload)")]:
        ax.text(120,z,t,fontsize=9,va="center",color="#333")
    ax.text(0,75,"PASS-THROUGH Oe45",ha="center",color="r",fontsize=10)
    ax.set_title("RU85 ROTARY STAGE -- CROSS-SECTION / CUTAWAY (parametric schematic)\n"
                 "shows the INTERNAL bolts a solid render hides; envelopes parameter-driven, internals simplified",fontsize=12)
    ax.set_xlim(-360,330); ax.set_ylim(-62,82); ax.set_aspect("equal"); ax.axis("off")
    fig.savefig(path,dpi=110,bbox_inches="tight"); print("wrote",path)

if __name__ == "__main__":
    cutaway()
