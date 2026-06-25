# Derived measurements — McMaster 6000N786 (T-Slotted Framing Fastener, Self-Align Ball Nut + M5 Screw)

Source mesh: `cad/6000N786.glb` (converted from `cad/6000N786_original.step` via `cascadio.step_to_glb`,
metres at glTF boundary; values below converted back to mm for readability). This is the combined
screw+nut assembly mesh (single named node `6000N786_T-Slotted Framing Fasteners`); McMaster's simplified
STEP export does not separate it into cleanly labeled sub-bodies (split-by-component gave 90 disjoint
mesh fragments, not clean screw/nut solids), so dimensions below are bounding-box / cross-section reads
off the combined mesh, not a clean single-part measurement.

## Overall bounding box (CAD-measured)
- Overall extents: **13.51 mm (X) x 12.10 mm (Y, nut axial/spring-throw direction) x 22.00 mm (Z)**
- Z spans -7.50 to +14.50 mm — consistent with the button-head screw shank/head (thread length 8 mm per
  spec) protruding on one end and the ball-nut body extending on the other.

## Cross-sections along Y (the insertion/compression axis of the spring-loaded ball nut)
| y (mm) | x-half-width (mm) | notes |
|---|---|---|
| 0 | ~2.4 | narrow region — nut body near its slot-insertion profile |
| 1 | ~3.2 | |
| 3 | ~5.2 | |
| 5 | ~6.4 (widest) | ball-nut body / wing widest point |
| 7 | ~3.9 | |
| 9–10 | ~3.3–4.4 | spring/ball region |

**Interpretation (CAD-measured, not manufacturer-confirmed):** the nut body's narrow/insertion profile
(~4.8 mm wide at its narrowest sectioned point near y=0) is consistent with a body sized to enter an 8 mm
slot opening before the spring-loaded ball mechanism seats it in the wider channel. This is a plausibility
check only — it does NOT independently prove the 8 mm-slot fit. The fit claim is established by the
part's own spec table (`For Rail Height: Single 1 1/2", 40mm`), which is manufacturer-confirmed evidence,
not this CAD reading.

## Confirmation status of feature claims
- **M5 thread**: manufacturer-confirmed (spec field `Fastener Thread Size: M5`, `Fastener Thread Length: 8mm`).
- **8 mm slot fit**: manufacturer-confirmed indirectly — 6000N786's own spec states `For Rail Height: Single
  1 1/2", 40mm`, and the companion extrusion 6575N203 ("Single Four Slot Rail... 40 mm Square") states its
  own `T-Slot Width: 8mm` directly in its spec table. McMaster does not print a "T-Slot Width" field on the
  nut/fastener-set product page itself — the nut's compatibility is stated in terms of rail height/series,
  cross-referenced to the rail's own slot-width spec. No direct numeric "8 mm slot" statement appears
  printed on 6000N786's own page. Flagging this as the one unresolved/inferred linkage (see report.json).
- **Drop-in, spring-loaded ball nut**: manufacturer-confirmed (`Nut Style: Self-Aligning Spring-Loaded Ball`,
  `Fastener Installation Type: Drop In`).
- **CAD body width vs 8 mm slot**: CAD-measured only, plausibility-level, not proof.
