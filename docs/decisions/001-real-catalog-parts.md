# 001 — Use exact real catalog parts for rigid hardware

**Decision:** Every rigid physical part is a real catalog part (McMaster generic hardware, Misumi FA/motion)
with its real CAD. No fabricated boxes, placeholder geometry, or "modelled as a box."

**Why:** A box has no holes, faces, or datums — nothing to mate against or to see — so it makes every check and
every render a lie. Broken assemblies hid behind placeholder geometry. Catalog parts also carry baked-in
attachment logic that collapses the design space.

**Consequences:** If a role seems to need a fabricated part, that's a signal to find the catalog part (mounted
bearings, standoffs, belt clamps, mounting plates, idlers, T-nuts all exist) or change the design so a catalog
part fits. The only allowed generated geometry is a genuinely flexible element (a belt loop) built from its
catalog spec — see [005](005-real-belt-before-capture.md).
