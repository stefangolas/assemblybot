# 003 — No phantom hardware

**Decision:** Do not invent missing screws, nuts, spacers, brackets, or belts to make an attachment close. A
missing fastener is a part to FIND, not to assume. Clearance and thread closure are separate conditions; a
clearance pass-through is not a hold until a real closing part (screw/nut) or confirmed integral geometry
exists.

**Why:** Residual-green attachments with no real fastener carrying the load are the canonical failure (a pulley
"coaxial" to an abstract axle with no screw; a clamp "coplanar" to a belt it never grips). The load-path gate
requires a continuous chain of real, geometry-checked, fastener-closed edges to ground.

**Consequences:** An attachment instance may only bind accepted canonical parts. If closure needs a part not in
the BOM (shims, a T-nut, a jaw), it stays `UNHELD`/`PROVISIONAL` and that missing part becomes a discovery task
— surfaced as a number by the gate, never silently passed. Do not author an attachment against a part that does
not yet exist (e.g. don't wire a T-slot mount before the real T-nut is fetched).
