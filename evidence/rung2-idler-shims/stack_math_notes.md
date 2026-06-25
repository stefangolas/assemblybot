# Stack-math check — rung2-idler-shims

## Manufacturer-confirmed inputs

- Axle = 96654A131 (McMaster, manufacturer-confirmed via product page):
  - Shoulder diameter: 5 mm (tolerance -0.025 to 0 mm)
  - Shoulder length: 16 mm (tolerance 0 to +0.05 mm)
  - Head diameter: 9 mm, head height: 4 mm
  - Thread: M4 x 0.7 mm, thread length 5 mm (separate from the 16 mm shoulder)

- Idler = SHTF20S3M100-5 (Misumi, NOT independently re-verified by this job -- the job packet's own
  estimates are taken as given since this packet's scope is the shims, not the idler):
  - Inner race recessed ~3 mm inside Ø22 flanges (packet estimate)
  - Flange opening ~Ø10 (packet estimate)
  - Race width ~9 mm (packet estimate, derived from "16mm shoulder ≈ shim + ~9mm race + shim")

## Arithmetic (using packet's own framing)

Shoulder length budget: 16 mm
Race width (packet estimate): ~9 mm
Remaining budget for two shims: 16 - 9 = 7 mm total -> ~3.5 mm per side if split evenly.

This 7 mm total / 3.5 mm-per-side figure is UNRESOLVED/DERIVED FROM THE PACKET'S OWN ESTIMATE, not
independently measured by this job (the idler race width was not CAD-measured here). Treat the "3.5mm
each" target as approximate, not exact -- real required thickness = (16 mm - actual race width) / 2,
and the actual race width should be CAD-measured or drawing-confirmed against the idler's own evidence
bundle before final selection.

## Option A: single/double-layer "round shim" stack, OD = 10 mm (3088A693 / 3088A203 family)

| Build | PNs | Total thickness (both sides) | Notes |
|---|---|---|---|
| 2x 1.5mm shims (one each side) | 3088A693 + 3088A693 | 3.0 mm | under-fills 7mm target by 4mm -- WRONG if 7mm total is correct |
| 2x 2mm shims (one each side) | 3088A203 + 3088A203 | 4.0 mm | still short of 7mm if that figure holds |
| 1.5mm + 2mm combo per side (2 shims/side) | 2x(3088A693+3088A203) | 7.0 mm exact | matches the 7mm total target if split as ~3.5mm/side using a 1.5+2mm pair per side |

OD = 10 mm exactly. **This equals, not clears, the packet's "~Ø10" flange-opening estimate.** Real fit
depends on the idler's actual flange-ID tolerance (unknown here) -- a flange opening that measures
9.9 mm would make this shim interfere with the flange instead of bearing only on the race. CONTRADICTS
the literal "OD < 10 mm" hard requirement as worded; flag as a risk, not a clean pass.

## Option B: "shoulder-shortening" shim stack, OD = 7.82 mm (91437A406 / 96945A306 family)

OD = 7.82 mm -- clears a Ø10 (or even Ø9) flange opening with comfortable margin. This is the
strictly-correct choice against the "OD < 10 mm, bear only on inner race" hard requirement.

Available thickness: 0.005" (0.127mm), 0.01" (0.254mm), 0.031" (0.787mm) per shim, in 18-8 or 316
stainless. McMaster's own product copy for this family explicitly endorses stacking ("slide these
shims under the screw head... stack multiple shims to achieve the exact shoulder length").

To reach ~3.5 mm per side using only 0.031" (0.787mm) shims:
  3.5 / 0.787 ≈ 4.4 -> needs 4-5 shims per side, i.e. 8-10 shims total across both sides.

McMaster's general shim guidance (seen on the round-shim family page) warns: "stacking more than four
may cause them to shift... fewer shims are better." 4-5 per side is at or beyond that informal limit --
a real risk for stack stability/squareness, though the warning was written for the round-shim family,
not lab-tested specifically for the shoulder-shortening family.

Mixed-thickness stacking reduces shim count: e.g. one 0.031" (0.787mm) + a few thinner ones. Using
0.031"+0.01"+0.01" = 0.787+0.254+0.254 = 1.295mm -- still well short of 3.5mm with only 3 pieces;
reaching 3.5mm per side with this family's thickest piece being 0.787mm unavoidably needs 4+ shims per
side regardless of mixing.

## Recommendation given the conflict

Neither shortlisted family cleanly satisfies BOTH "exactly ~3.5 mm in one or two pieces" AND
"OD strictly < 10 mm" at the same time:

- The single-piece-per-side, ~3.5mm-thick path (carbon-steel round shims, 1.5+2mm combo) hits the
  thickness target cleanly but its OD (10mm) is flush with the estimated flange clearance, not
  comfortably inside it.
- The OD-safe path (shoulder-shortening shims, OD 7.82mm) only comes in thin increments (max 0.787mm),
  so reaching ~3.5mm needs a 4-5-deep stack per side, which is at/beyond McMaster's own stacking
  caution and may be hard to keep square/non-shifting in service.

**This is reported as a genuine, unresolved trade-off for the lead to decide, not resolved by this
worker.** A possible third path not pursued in depth here: query whether a single-piece OD<10mm
spacer/bushing of ~3.5mm length and 5mm bore exists outside the "shim" categories (the nylon spacer
lead, 94639A130, was the closest hit but is the wrong length at 12.7mm and McMaster's
round-unthreaded-spacer metric ID=5mm category page would not render its product grid headless in
this session -- worth a follow-up pass with a different facet combination or a logged-in/visible-tab
retry).
