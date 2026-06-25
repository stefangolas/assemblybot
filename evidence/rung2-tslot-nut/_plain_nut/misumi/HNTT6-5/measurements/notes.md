# HNTT6-5 CAD measurements

Source: `cad/HNTT6-5_original.step` (MISUMI STEP_AP203, fetched via in-page
`cadFormatList`/`cadDownload` hands-off flow), converted via `cascadio.step_to_glb`
to `cad/HNTT6-5_converted.glb` (metres at the glTF boundary; library part itself
modeled in mm-equivalent envelope below).

## Bounding-box (CAD-measured)

Single watertight body (1 geometry, 386 vertices) loaded via
`trimesh.load(..., force='scene')`.

- Overall envelope: **14.00 mm (X) x 6.30 mm (Y) x 15.00 mm (Z)**
- This matches the manufacturer drawing's front-view footprint (14 x 15 mm)
  and the drawing's narrower "5.5" / wider "6.3" two-tier base-thickness
  callout — the CAD envelope height (6.30 mm) corresponds to the drawing's
  outer/widest base dimension (6.3 mm), i.e. the full nut body height
  including the wider lower flange. CAD-measured, consistent with but not
  independently authoritative over the manufacturer drawing.

## Bore / thread region

- Central bore vertices cluster at radii ranging ~0.28-2.06 mm from the
  bore axis, forming a helical (non-cylindrical-constant-radius) surface --
  i.e. CAD models the bore as an actual helical thread form, not a plain
  cylindrical clearance hole. This is CAD-measured corroboration only; the
  THREAD IDENTITY (M5) is manufacturer-confirmed independently via the
  product page's own "Thread Nominal M(mm)" = M5 configuration field and
  the part number HNTT6-5 itself (the "-5" suffix is the M-value per the
  documented PN grammar `HNTT6-{M}`).
- Did not attempt to fit an exact ISO M5 major/minor diameter from the raw
  vertex cloud (thread crest/root vertex sampling is too coarse at this
  mesh resolution for a reliable +/-0.05 mm thread-class claim) -- the
  thread spec is manufacturer-confirmed from the spec table, not re-derived
  from CAD.

## What CAD does NOT establish here

- CAD alone does not establish the slot-width fit. That claim rests on the
  manufacturer's own catalog drawing dimension (see source/catalog_page.pdf,
  page 1, "HFS6 Series" icon: literal dimension "8" on the groove-width
  callout) -- a manufacturer-confirmed, same-document numeric statement,
  independent of CAD.
- No offscreen renderer (pyglet) was available in this environment to
  produce an isometric PNG render; numeric bounding-box/vertex measurement
  was used instead. Flag for the lead if a visual render is wanted before
  final acceptance -- the GLB is saved and renderable later with the
  project's normal render pipeline.
