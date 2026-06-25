# MANUFACTURING DRAWING — `ROTARY_ADAPTER_RU85_S5M_REV_A`

- **Revision:** A
- **Released:** NO — held by the revision gate (Section 7).
- **Material:** 6061-T651 aluminum
- **Evidence type:** `custom_drawing`
- **Drawing units:** millimetre. glTF boundary metres.

## Function

The rotating adapter. Contacts **only the RU85 inner race**, bolts to the inner race, locates and
bolts the 72-tooth S5M pulley, carries four catalog M6 standoffs for the tabletop, and preserves a
45 mm central pass-through.

## Coordinate system (part-local)

- Origin: bearing + pulley axis.
- **Z = 0: lower inner-race contact face.** +Z points toward the pulley / tabletop.
- RU85 hole pattern clocked **22.5°** from +X; pulley pattern clocked **0°** from +X.

## Envelope

- Outside diameter **Ø180.00**.
- Top working face **Z = 12.00**; max height at pulley pilot **Z = 15.00**; bottom inner-race contact
  face **Z = 0**.
- Deburr; external edge break 0.5 × 45° max.

## Features

### F1 — Central pass-through
- 1 × through hole **Ø45.00 (+0.10 / 0.00)**, on the part axis. (Task verification #9.)

### F2 — Lower inner-race contact boss (underside annulus)
- OD **Ø76.00 ±0.05**, ID = the Ø45 central hole; contact plane **Z = 0**.
- Flatness of contact annulus **0.02**; Ra ≤ 1.6 µm.
- **Relieve every underside surface outside Ø76.00 upward by 0.50 ±0.05 mm.**
- Result: the Ø76 boss contacts the inner ring; the rest stays ≥ 0.45 mm clear of the stationary
  outer ring. **Boss OD must never exceed RU85 ds = 77 mm.** (Task verification #2, #3.)

### F3 — RU85 inner-race mounting holes (8 × counterbored clearance)
- Through **Ø5.50**; counterbore **from the Z=12.00 top working face**, **Ø9.50 × 5.50 deep**.
- PCD **65.00** (R 32.50); angular **22.5 + 45n°**.
- Positional tol **Ø0.05** to axis + inner-race contact face.
- Coordinates (mm):

  | Hole | X | Y |
  |---:|---:|---:|
  | 1 | 30.026 | 12.437 |
  | 2 | 12.437 | 30.026 |
  | 3 | -12.437 | 30.026 |
  | 4 | -30.026 | 12.437 |
  | 5 | -30.026 | -12.437 |
  | 6 | -12.437 | -30.026 |
  | 7 | 12.437 | -30.026 |
  | 8 | 30.026 | -12.437 |

- Fastener: **8 × M5×16 SHCS** into the RU85 inner ring threads (length subject to engagement
  verification). **All heads finish at or below Z=12.00** so the pulley seats fully. (Verification #5.)

### F4 — Pulley locating pilot (raised annulus, top)
- OD **Ø50 h6**, ID = the Ø45 central hole.
- Pilot height **3.00 ±0.03** above the Z=12.00 face → pilot top **Z = 15.00**.
- Concentricity/runout to the inner-race contact boss **0.02 TIR**.
- Locates the MISUMI pulley's Ø50 H7 bore. The 4 screws CLAMP; the pilot LOCATES. (Verification #6.)

### F5 — Pulley mounting threads (4 × M5×0.8-6H)
- PCD **85.00** (R 42.50); angular **0, 90, 180, 270°**.
- Min full thread depth **10.0**; positional tol **Ø0.05** to the pulley pilot axis.
- Coordinates (mm):

  | Hole | X | Y |
  |---:|---:|---:|
  | 1 | 42.500 | 0.000 |
  | 2 | 0.000 | 42.500 |
  | 3 | -42.500 | 0.000 |
  | 4 | 0.000 | -42.500 |

- Fastener: **4 × M5 SHCS** through the pulley's four Ø5.5 holes; length set only after measuring the
  pulley mounting-web thickness from its downloaded CAD. (Verification #7.)

### F6 — Tabletop-standoff threads (4 × M6×1.0-6H blind)
- Coordinates X = ±55.00, Y = ±55.00.
- Min full thread depth **10.0**; tap-drill depth **13.0** min; positional tol **Ø0.10**.

  | Hole | X | Y |
  |---:|---:|---:|
  | 1 | 55.000 | 55.000 |
  | 2 | -55.000 | 55.000 |
  | 3 | -55.000 | -55.000 |
  | 4 | 55.000 | -55.000 |

- Fastener: **4 × catalog M6 standoffs**, nominal length 30 mm, OD ≤ 12 mm. 30 mm clears the nominal
  22 mm pulley body axially. (Verification #8.)

## Surface relationships
- Z=12.00 pulley seat ∥ Z=0 inner-race contact face within 0.03.
- Pulley pilot axis ⟂ inner-race contact face within Ø0.03 over its 3 mm height.
- Pulley pilot + central through-hole concentric within 0.02 TIR.
- General unlisted linear ±0.10; angular ±0.5°.

## Drawing → CAD reconciliation
- CadQuery model built directly in this part-local frame (mm) → drawing_to_cad identity.
- Reconcile by measuring: Ø45 bore, Ø76 boss OD + 0.50 relief step, Ø50 h6 pilot OD + 3 mm height,
  both bolt PCDs (65 inner, 85 pulley), standoff square, and that all F3 heads sink ≤ Z=12.
