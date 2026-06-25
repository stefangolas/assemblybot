# Skill: McMaster-Carr (generic hardware)

Use McMaster for generic MRO/fasteners (shoulder screws, shims, washers, T-slot nuts, framing) — things Misumi
lacks or when Misumi can't be warmed. Different Akamai property than Misumi (a Misumi block doesn't affect it;
guest CAD needs no login).

## Strengths vs weaknesses

- **Strength:** detail/product pages work — `data/mcmaster_fetch.read_specs(pn)` returns title + spec text, and
  CAD downloads once you HAVE the PN. The page `document.title` validates a PN (descriptive title = real; bare
  "McMaster-Carr" = invalid/shell/not-rendered).
- **Weakness — DISCOVERY:** category/listing pages render PNs in a **virtualized table** that is NOT in the DOM
  text/anchors and renders **BLANK headless** (you get only facet-sidebar labels, ~2.7 KB), and
  `captureScreenshot` tends to **time out**. So *finding* a PN from a category is the hard part headless.
- A temporary headless failure is NOT "McMaster never works" — it's the virtualized grid. Pivot, don't grind.

## When to pivot vs scrape

- Do NOT repeatedly poll/screenshot an empty virtualized grid. If the product grid won't populate (innerText is
  just facet labels), **stop** and either: probe a candidate PN directly with `read_specs`, use the search box
  redirect to a faceted URL whose text has PNs, or pivot the search to Misumi (preferred — see
  `skills/vendor-misumi.md`).
- Facet URLs compose (`/products/<category>/<facet>~<value>/`) but are loose — re-read the product's own
  "For …" fields for real fit. Note McMaster groups by **rail height**, not slot width — verify slot width from
  the part's own drawing.

## CAD download (no sign-in)

Warm cdp-chrome, **fresh ACTIVE tab** (`Target.createTarget` + `Target.activateTarget`; the CAD widget
lazy-renders only on the active tab — a background tab stays a spinner), poll ~30 s for `a[download]` ending
`.STEP`, then a **TRUSTED** `Input.dispatchMouseEvent` click at the link's `getBoundingClientRect` centre
(synthetic `.click()` and in-page `fetch` of the href both 403). STEP lands in `~/Downloads`; `shutil.move` →
`cad/<PN>.step`; `cascadio.step_to_glb` (metres); measure. Prefer "3-D STEP no threads"; fall back to "3-D
STEP". Also grab the 2-D drawing/PDF (the geometry+semantics authority) — read the dimensioned drawing, not the
`.dwg`. Helper: `data/mcmaster_fetch.py` (`read_specs`, `download_step`). Close stale McMaster tabs after —
piled heavy tabs degrade CDP.

## Circuit breaker

A burst of headless hits can trip Akamai's login wall (bare "McMaster-Carr" title) — IP/sensor-cookie
reputation, not an account requirement; curl/spoofing won't help (the download URL is generated client-side).
Back off; re-warm by real browsing in that window.

Related memories: [[mcmaster-cdp-download]], [[mcmaster-fetch-helper]], [[mcmaster-cad-no-signin]],
[[catalog-scrapeability]].
