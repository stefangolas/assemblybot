# Stage: Part Authoring

Allowed:
- Author immutable part definitions from evidence.
- Generate allowed flexible belt meshes from catalog parameters.
- Generate standard washers from the governing ISO/DIN/ASME dimensions.
- Generate sheet-stock panels from explicit width/height/thickness/material/hole parameters. Do not fetch vendor CAD for flat plastic or sheet-metal stock when geometry is fully parameterized by the released specs.
- Use configured vendor CAD for T-slot extrusion rails when available. Only create derived cut/swept rail geometry when the project explicitly licenses that fallback and labels it as derived from vendor evidence.
- Author T-slot extrusion attachment as continuous slot domains, not invented repeated nut stations. Each slot should expose a bounded `swept_profile` receiver and `continuous_domain`; clamp/nut placement must stay inside the rail ends by the inserted part footprint or specified end clearance.
- Generate licensed custom rigid parts only after the custom-license record exists.

Forbidden:
- Putting assembly placement into library part definitions.
- Omitting real holes, pilots, seats, threads, or fasteners from canonical parts.
- Treating one vendor's T-slot profile as interchangeable with another vendor's profile unless the slot width, slot depth, rail section, core holes, and attachment hardware family match the selected evidence.

Exit criteria:
- Part definitions and CAD assets exist for all canonical structural roles.
