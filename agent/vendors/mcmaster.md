# McMaster Prompt Notes

- Use McMaster for generic hardware, fasteners, shims, collars, bearings, and MRO parts when MISUMI is not appropriate.
- Discovery path: first search the web for `"<part description>" McMaster` or `"<standard/designation>" "McMaster-Carr"`, then probe candidate PNs with `data.mcmaster_fetch.read_specs`. Record the query and search engine. Do not report a no-hit as "Google returned nothing" unless Google itself was actually used.
- Verify candidates from product detail/spec pages, not virtualized category grid assumptions.
- Use category/facet pages as PN discovery indexes only. Narrow facet URLs can expose product rows in `document.body.innerText`, but a facet list does not prove one PN satisfies every visible facet; promote only after the product page confirms the exact fields.
- Treat product-page titles as a fast rejection filter. If the title names the wrong product class, rail family, or use case, reject the PN before spending time on CAD.
- For configurable stock, one PN plus ordered dimensions may satisfy several BOM lengths. Record the configured length range/increment from the product page instead of searching for separate length-specific PNs.
- Record rejected near-matches as evidence outputs, especially when profile, width, thread, bore, or vendor ecosystem is close but wrong. This prevents repeated discovery loops.
- CAD and drawings are evidence; source product text is not enough for attachment geometry.
- If discovery stalls in the catalog UI, record the blocker and pivot rather than guessing.
- Use `data.mcmaster_fetch` helpers for product pages; they must close their own CDP target after every probe/download.
- Washers can usually be standard-generated from ISO/DIN/ASME dimensions. McMaster product pages can serve as existence/procurement evidence, but the geometry should come from the standard where available.
- For T-slot rails, prefer configured McMaster CAD for the ordered length. Do not substitute a McMaster rail for MISUMI HFS8 unless the controlling profile dimensions and hardware ecosystem match. Derived cut/swept rail geometry is a fallback, not default canonical evidence.
