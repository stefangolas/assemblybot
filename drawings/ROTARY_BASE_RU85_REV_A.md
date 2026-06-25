# MANUFACTURING DRAWING — `ROTARY_BASE_RU85_REV_A`

- **Revision:** A
- **Released:** NO — held by the revision gate (Section 7 of the task) until RU85 STEP/drawing
  reconciled, 72T pulley STEP downloaded, fastener lengths checked, all isolated attachment checks
  pass, and section renders confirm the correct race is contacted.
- **Material:** 6061-T651 aluminum
- **Evidence type:** `custom_drawing`
- **Drawing units:** millimetre. CAD (glTF) boundary is metres (cascadio/trimesh convention).

## Function

Stationary base plate. Supports **only the RU85 outer race**, anchors the bearing to the 40 mm
T-slot frame, and leaves the inner race + 55 mm bearing bore unobstructed. The motor mount attaches
to the extrusion frame, NOT to this plate — there are no motor holes here.

## Coordinate system (part-local)

- Origin: bearing axis at the center of the plate.
- X, Y: parallel to plate edges.
- **Z = 0: top bearing-mounting surface (Datum A).** Plate extends to **Z = -15.00**.
- Bearing-hole pattern zero angle is clocked **22.5°** from +X.

## Blank / envelope

- Finished size: **220.00 × 220.00 × 15.00 mm**.
- Deburr all edges; external edge break **0.5 mm × 45° max**.

## Datums & critical surfaces

| Datum | Feature | Control |
|---|---|---|
| A | complete top bearing-mounting face (Z=0) | flatness 0.03 over the 120 mm bearing footprint; Ra ≤ 1.6 µm |
| B | central bore axis | (datum for hole positions) |
| C | one plate edge | (rotational datum) |
| — | bottom face (Z=-15) | parallel to A within 0.05 over the plate |

## Features

### F1 — Central clearance opening (pass-through)
- 1 × through hole, **Ø94.00 (+0.10 / 0.00)**, centered at (0, 0).
- Through the full 15 mm thickness.
- Rationale: > RU85 minimum outer-ring support opening **Dh = 93 mm**, so the base **cannot contact
  the rotating inner ring**. (Task verification #1.)

### F2 — RU85 outer-race threads (8 × M5×0.8-6H blind tapped)
- PCD **105.00** (R 52.50); angular **22.5 + 45n°**, n=0..7.
- Min full thread depth **10.0**; tap-drill depth **13.0** min. (Blind — does NOT break through to Z=-15.)
- Positional tol **Ø0.05** to A|B|C.
- Hole-center coordinates (mm):

  | Hole | X | Y |
  |---:|---:|---:|
  | 1 | 48.504 | 20.091 |
  | 2 | 20.091 | 48.504 |
  | 3 | -20.091 | 48.504 |
  | 4 | -48.504 | 20.091 |
  | 5 | -48.504 | -20.091 |
  | 6 | -20.091 | -48.504 |
  | 7 | 20.091 | -48.504 |
  | 8 | 48.504 | -20.091 |

- Fastener: **8 × M5×18 SHCS** into the bearing outer ring (unless CAD/tool-access verification forces
  a different standard length). Verify no screw bottoms in the blind thread (engagement < 13 mm drill,
  ≥ outer-ring through thickness + washer + thread engagement).

### F3 — Extrusion-frame anchor holes (8 × counterbored clearance)
For a 220 mm-square frame of 40×40 T-slot extrusion with member centerlines at X = ±90, Y = ±90.
- Through **Ø6.60**; counterbore from top **Ø11.00 × 6.50 deep**.
- Intended fastener: **M6 SHCS into a proven matching T-slot nut** (catalog).
- Positional tol **Ø0.15** to A|B|C.
- Coordinates (mm):

  | Hole | X | Y |
  |---:|---:|---:|
  | 1 | -60.000 | 90.000 |
  | 2 | 60.000 | 90.000 |
  | 3 | -60.000 | -90.000 |
  | 4 | 60.000 | -90.000 |
  | 5 | 90.000 | -60.000 |
  | 6 | 90.000 | 60.000 |
  | 7 | -90.000 | -60.000 |
  | 8 | -90.000 | 60.000 |

## Drawing → CAD reconciliation
- Identity: part-local frame == CAD frame (scale 1, identity rotation, zero translation).
- The CadQuery model is built directly in this part-local frame (mm), so drawing_to_cad is identity
  by construction; reconcile by measuring F1 diameter, both PCDs, and the counterbore depth back from CAD.
