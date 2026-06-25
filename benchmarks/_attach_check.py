"""Annotated isolation look-check for ONE attachment (Hard Rule 1b).

Render JUST the mating pair (inserted part + its acceptor + any fastener) projected
onto a plane, as filled silhouettes in world mm, with DIMENSION ANNOTATIONS overlaid
(bore vs shaft diameter, seating gap, span, reach, tooth pitch). The point is to SEE
whether the parts are physically held by a real feature -- not merely residual-green.

Usage (programmatic): build a spec dict and call render(spec, out_png). See the
__main__ block for the idler<->bracket<->screw example.

spec = {
  "parts": [{"glb": "/abs/or/cad-rel.glb", "R": 3x3, "t_mm": [..], "color": "#rrggbb", "label": "idler"}],
  "view":  "yz" | "xz" | "xy",     # which world plane to project onto
  "dims":  [{"p": [a0,a1], "q": [b0,b1], "text": "Ø5.0 bore", "side": 1}],  # 2D pts in the view plane (mm)
  "title": "...",
}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import trimesh
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.spatial import ConvexHull

ROOT = Path(__file__).resolve().parent.parent
AX = {"x": 0, "y": 1, "z": 2}


def _world_pts(glb, R, t_mm):
    p = glb if Path(glb).is_absolute() else str(ROOT / glb.lstrip("/"))
    m = trimesh.load(p, force="mesh")
    v = np.asarray(m.vertices) * 1000.0                 # metres -> mm
    return (np.asarray(R) @ v.T).T + np.asarray(t_mm)


def render(spec, out_png):
    view = spec.get("view", "yz")
    h, w = AX[view[0]], AX[view[1]]
    fig, ax = plt.subplots(figsize=(9, 7))
    for part in spec["parts"]:
        P = _world_pts(part["glb"], part["R"], part["t_mm"])[:, [h, w]]
        # downsample for hull speed
        if len(P) > 4000:
            P = P[np.random.choice(len(P), 4000, replace=False)]
        try:
            hull = ConvexHull(P)
            poly = P[hull.vertices]
            ax.fill(poly[:, 0], poly[:, 1], color=part.get("color", "#888"),
                    alpha=0.45, ec=part.get("color", "#888"), lw=1.5,
                    label=part.get("label", ""))
        except Exception:
            ax.scatter(P[:, 0], P[:, 1], s=2, color=part.get("color", "#888"),
                       label=part.get("label", ""))
    # dimension annotations: double-headed arrow + text
    for d in spec.get("dims", []):
        p, q = np.array(d["p"], float), np.array(d["q"], float)
        ax.annotate("", xy=q, xytext=p,
                    arrowprops=dict(arrowstyle="<->", color="#e0e0e0", lw=1.6))
        mid = (p + q) / 2
        ax.text(mid[0], mid[1], "  " + d["text"], color="#ffec8b", fontsize=11,
                ha="left", va="center", weight="bold",
                bbox=dict(boxstyle="round,pad=0.2", fc="#222", ec="none", alpha=0.7))
    ax.set_aspect("equal")
    ax.set_facecolor("#15171a")
    fig.patch.set_facecolor("#15171a")
    ax.tick_params(colors="#aaa")
    for s in ax.spines.values():
        s.set_color("#444")
    ax.set_xlabel(f"{view[0]} (mm)", color="#ccc")
    ax.set_ylabel(f"{view[1]} (mm)", color="#ccc")
    ax.set_title(spec.get("title", "attachment check"), color="#fff")
    ax.legend(facecolor="#222", edgecolor="#444", labelcolor="#ddd", loc="best")
    ax.grid(True, color="#2a2e33", lw=0.5)
    fig.tight_layout()
    fig.savefig(out_png, dpi=110)
    plt.close(fig)
    print("wrote", out_png)


if __name__ == "__main__":
    render(json.load(open(sys.argv[1])), sys.argv[2])
