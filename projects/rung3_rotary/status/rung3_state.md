# Rung 3 State: RU85 Belt-driven Rotary Stage

**Status**: Verified on disk (Gate: ALL HELD)
**Date**: 2026-06-24

## Mechanism Overview
- **Rotating Output**: A 3-part assemblable stack (fixes the previous one-piece "drum" trap):
  - Lower adapter (REV_A)
  - 72T S5M pulley mounted on the adapter's Ø50 pilot
  - Bolt-on cap (4× M5×35 spanning the pulley at PCD85, inside the belt)
  - 200mm tabletop on the cap (4× M6, fanned to ±55 above the belt)
- **Load Path**: Payload load goes: tabletop → cap → bolts → adapter → inner ring. It *never* passes through the pulley.
- **Joint**: Crossed-roller RU85UUC0 bearing serves as the revolute joint. Race-segregation is strictly enforced (8 bolts to the inner ring, 8 to the outer).
- **Drive**: 4:1 reduction (72/18T), generated S5M belt loop, NEMA23 motor mounted on the fixed frame.

## Gate Verification
- The canonical build (`benchmarks/rung3_assembly.py`) successfully generates `projects/rung3_rotary/out/rung3_assembly.json`.
- The assembly consists of 53 parts (including 40 fasteners).
- **Gate**: `ALL HELD` (every body is `HELD_CONFIRMED`).
- 4 custom parts (base, two adapter revs, cap) cleanly pass the DFM edge-distance and thread-engagement/length gates.

## Remaining Work (~20%)
- Catalog-fetch tail (real branded NEMA23 + adjustable mount).
- Place fastener bodies explicitly in the render.
- mplot3d iso/top schematic generation.
- Formal revision sign-off.
