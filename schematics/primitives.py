"""Parametric SCHEMATIC primitives (mm). Cross-section + helpers for design-review
sketches -- NOT CAD, NOT fit-validation. Cross-section primitives draw in the (radius, z)
plane (axis = z); each annular/disc part shows as a left+right pair so internal features
(bores, bolts) are visible. Honest schematic: envelopes are parameter-driven, internals
simplified until exact CAD is substituted.
"""
from matplotlib.patches import Rectangle

# group -> visual style (grayscale-safe: alpha + hatch + edge weight, not color alone)
GROUP = {
    "stationary": dict(facecolor="#c9ccd1", edgecolor="#33363b", hatch="////", lw=1.3, alpha=1.0),
    "rotating":   dict(facecolor="#7fb0e0", edgecolor="#1d3f63", lw=1.5, alpha=0.95),
    "pulley":     dict(facecolor="#74c79a", edgecolor="#1d6b46", lw=1.3, alpha=0.95),
    "payload":    dict(facecolor="#e0c060", edgecolor="#6f5d12", lw=1.3, alpha=0.95),
    "fastener":   dict(facecolor="#3a3f47", edgecolor="#0a0c0f", lw=1.0, alpha=1.0),
    "flexible":   dict(facecolor="#222428", edgecolor="#000", lw=1.0, alpha=1.0),
}

def ring(ax, ri, ro, z0, z1, group="stationary", **kw):
    """Cross-section of an annulus/disc: a rectangle each side of the axis (x=+/-r)."""
    st = {**GROUP[group], **kw}
    for sgn in (-1, 1):
        x = sgn * ro if sgn < 0 else ri
        ax.add_patch(Rectangle((x, z0), ro - ri, z1 - z0, **st))

def bar(ax, half_w, z0, z1, group="payload", **kw):
    st = {**GROUP[group], **kw}
    ax.add_patch(Rectangle((-half_w, z0), 2 * half_w, z1 - z0, **st))

def block(ax, x0, x1, z0, z1, group="stationary", **kw):
    st = {**GROUP[group], **kw}
    ax.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0, **st))

def bolt(ax, r, z_head_top, length, dia=5.0, head_dia=8.5, head_h=5.0, group="fastener", **kw):
    """A cap/cup screw in cross-section at radius r (drawn both sides). Head at the TOP,
    threaded shank pointing -z (down) into the receiver. z_head_top = top of the head."""
    st = {**GROUP[group], **kw}
    for sgn in (-1, 1):
        cx = sgn * r
        # head
        ax.add_patch(Rectangle((cx - head_dia/2, z_head_top - head_h), head_dia, head_h, **st))
        # shank
        ax.add_patch(Rectangle((cx - dia/2, z_head_top - length), dia, length - head_h, **st))

def crossed_rollers(ax, r, z_mid, s=3.0):
    """An 'X' each side to denote the crossed-roller row (alternating +/-45 rollers)."""
    for sgn in (-1, 1):
        ax.plot([sgn*r-s, sgn*r+s], [z_mid-s, z_mid+s], "k", lw=0.7)
        ax.plot([sgn*r-s, sgn*r+s], [z_mid+s, z_mid-s], "k", lw=0.7)

def passthrough(ax, r, z0, z1):
    ax.plot([-r, -r], [z0, z1], "r--", lw=1.0); ax.plot([r, r], [z0, z1], "r--", lw=1.0)

def centerline(ax, z0, z1):
    ax.plot([0, 0], [z0, z1], "k-.", lw=0.7)
