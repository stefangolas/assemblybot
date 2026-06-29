# Stage: Catalog Discovery

Allowed:
- Search MISUMI first, then McMaster where appropriate.
- For McMaster discovery, search the web for `"<part description>" McMaster` or `"<standard/designation>" "McMaster-Carr"` before driving virtualized catalog grids; record the search engine/query and treat results as leads only.
- For McMaster, use category/facet pages only to extract candidate PNs. Product-page `read_specs` confirmation is required before any role can be accepted.
- Reject obvious title-level mismatches immediately and record the rejection when the PN is likely to recur.
- Record candidates, evidence, CAD availability, and rejection reasons.
- Propose design changes when catalog parts do not fit.
- Classify standard washers as standard-generated candidates when their geometry is controlled by ISO/DIN/ASME dimensions.
- For T-slot extrusions, record the selected vendor/profile, configured length, CAD availability, and any rejected near-equivalent profiles. Do not assume vendor-to-vendor profile equivalence.

Forbidden:
- Generating canonical custom rigid CAD for unresolved catalog roles.
- Publishing or claiming the build is complete.

Exit criteria:
- Every role has accepted catalog evidence, standard-generated status, generated-flexible catalog parameters, or a custom-license record.
- Every standard-generated role cites the controlling standard or accepted exemplar, and every vendor-profile role records CAD/profile evidence plus mismatches for rejected near-equivalents.
