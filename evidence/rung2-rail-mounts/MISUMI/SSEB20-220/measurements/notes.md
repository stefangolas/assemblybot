# Notes — SSEB20-220 rail mount-hole recovery

## Pull method
- Clean re-pull via `cadFormatList` -> `cadDownload` (STEP_AP203) in-page fetch on a fresh
  CDP tab (own tab, closed when done). `cascadio.step_to_glb` then `trimesh.load(force='scene')`.
- The fresh STEP file contains **2 named bodies**: `RAIL_SSEB20-220` and `BLOCK_SSEB20-220` —
  this re-pull did NOT lose the rail/block split (unlike whatever prior combined+split operation
  lost the mount-hole pattern). The isolated rail body has the full mount-hole geometry intact.

## Measurement method
- Loaded the isolated `RAIL_SSEB20-220` mesh, scaled mm (cascadio writes metres at the glTF
  boundary -> ×1000 here since this is raw single-part CAD inspection, not the assembly).
- Found all vertices on the top face (y = 11.0 mm = H1) that are NOT on the rectangular
  perimeter -> these trace 4 distinct circular hole rims.
- Circle-fit each cluster: 4 holes at x = 0, 60, 120, 180 mm, all centered at z = 0 (rail
  centerline), radius 4.75 mm (-> Ø9.5 mm counterbore).
- Walked the same (x,z) location through y to capture the counterbore step: profile is
  Ø9.5 mm from y=11 (top) down to y=5.5, then steps down to Ø6.0 mm from y=5.5 to y=0 (bottom
  face). This exactly matches the spec table's `d1 x d2 x h = 6 x 9.5 x 5.5` for the H=20 row.

## Cross-check against manufacturer spec table (Table 1, H=20 row)
```
H=20: L1-range 100~1000(160) | F=60 | G=20 | Counterbored Hole d1xd2xh = 6x9.5x5.5
```
- F (pitch) = 60 mm -> matches CAD-measured 60 mm spacing exactly.
- G (edge margin) = 20 mm -> matches CAD x=0 hole sitting 20 mm from the x=-20 rail end
  (and x=180 hole sitting 20 mm from the x=200 rail end); 20+60+60+60+20 = 220 = L. Consistent.
- d1 (through) = 6, d2 (counterbore) = 9.5, h (counterbore depth) = 5.5 -> all three match the
  CAD profile exactly.

## Cross-check against the drawing (drw_01_2014.gif / .png)
- "H6 Type" cross-section + side view drawing shows the rail with Ød1/Ød2/h counterbore
  profile and F/G dimension callouts in the same arrangement measured above. Confirms the
  table is describing this exact feature (not a different rail subtype).

## Thread vs clearance determination
- The spec table's rail-hole column is named **"Counterbored Hole d1xd2xh"** with NO thread
  designation — distinct from the **block carriage's** "S x l" mounting-screw column (which DOES
  list M2x1.5 / M3x3 / M4x6 etc., scoped to the carriage block, not the rail).
- The drawing's rail-hole callout is plain "Ød1" (no M-thread symbol).
- Conclusion: the rail mount holes are **plain clearance counterbored through-holes**, not
  tapped. This is manufacturer-confirmed (table column semantics + drawing symbol), not an
  inference from CAD diameter alone (per [[misumi-hole-type-codes]] / [[drawings-are-truth]]).

## What is still NOT manufacturer-named (left for the lead)
- The bolt/screw size that should be PASSED THROUGH this Ø6 mm clearance hole into the 40 mm
  extrusion's M5 T-slot nut is not specified on the SSEB20-220 rail's own documentation (Misumi
  sells guide rails hole-pattern-only; the customer supplies the screw). Ø6 mm clearance
  comfortably fits an M5 cap screw (typically Ø5.5 clearance) or M6 (typically Ø6.6 clearance —
  tighter fit at Ø6). Given the task's stated T-slot-nut pairing is **M5**, an M5 SHCS is the
  standard-derived choice for THIS clearance hole, but that final choice belongs to the lead
  (it is a fastener-selection decision, not a rail-evidence fact). Flagging as UNRESOLVED in the
  report rather than asserting it.
