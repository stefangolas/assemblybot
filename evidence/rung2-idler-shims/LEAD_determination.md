# Lead determination — idler shim diameter trade-off (2026-06-21)

The shim scout returned `MULTIPLE_CANDIDATES` and correctly escalated the OD-vs-thickness trade-off,
noting that "OD<10", "~3.5 mm/side", and "race ≈9 mm" were lead *estimates*. I re-measured the idler CAD
(`cad/SHTF20S3M100-5.glb`, mesh-section perpendicular to the bore axis X) to settle the geometry.

## Measured idler recess geometry (mm, mesh-section)
- bore (inner race ID): Ø5.0 (R2.5)
- **flange opening (recess wall a shim must fit inside): ≈ Ø9.8** (clean ring R4.9 at x=1.5, inside the near recess)
- flange OD: Ø22 (R11)
- recessed inner-race face at x=3 (near) and x=12 (far); race hub spans x=3..12 ≈ **9 mm**
- recess depth ≈ **3 mm per side** (flange face x=0 / x=15 to race face x=3 / x=12)
- race face the shim bears on = annulus Ø5 → ~Ø9.8

## Resolution
- The "OD < 10 mm" requirement is VALID and in fact slightly TIGHTER: **OD must be < ~9.8 mm** to enter the
  recess and bear on the race, not the rotating flange.
- **REJECT** round shims `3088A693`/`3088A203` (OD **10.0**) — they sit flush with / foul the ~Ø9.8 opening.
- **PREFER** the OD **7.82 mm** stainless shoulder-shim family (`91437A406` 18-8 / `96945A306` 316),
  ID5 — clears the opening, bears cleanly on the race annulus.

## Open interaction to resolve when wiring retention (NOT yet decided)
1. **Stack depth:** recess is ~3 mm/side but the 7.82 shims are 0.787 mm max → ~4 per side, at McMaster's
   own stacking caution (">4 may shift"). A **single-piece precision spacer, ID5.x / OD 8–9 (<9.8) / ~3 mm
   long**, would be mechanically cleaner than a 4-deep thin-shim stack — worth a targeted follow-up search
   (the scout's `94639A130` spacer was OD-ok Ø9.5 but 12.7 mm long → wrong length).
2. **Shoulder-length interaction:** 96654A131 shoulder = 16 mm but idler width = 15 mm. Stack 3+9+3 = 15 mm,
   so the 16 mm shoulder leaves ~1 mm before the head clamps → may NOT tension the race. Re-check at
   retention wiring: either a marginally thicker shim stack (~3.5 mm/side) or a shorter shoulder screw.

DIRECTION: 7.82 OD shoulder-shim family is the diameter-correct answer; before binding retention, prefer a
one-piece ~3 mm OD<9.8 ID5 spacer if one exists, and reconcile the 16 mm-shoulder/15 mm-idler clamp gap.
