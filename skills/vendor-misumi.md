# Skill: MISUMI (FA / motion parts)

**Default to Misumi for scraping** ([[catalog-scrapeability]]): once warm, classic `/vona2/detail/` pages are
server-rendered — `Runtime.evaluate` reads innerText, spec TABLES, the PN template, and drawing image URLs
cleanly, and CAD is a hands-off structured fetch.

## Hard session rules (each cost real time to learn)

1. **ONE long-lived `cdp-chrome` on :9222. NEVER kill+relaunch to recover a wedged tab.** A burst of
   relaunches / cold deep-links strips the Akamai sensor cookie and 403s `us.misumi-ec.com` **site-wide** for
   the instance (which also kills the CAD fetch — same session) and does NOT clear on retries. If a tab wedges,
   open a NEW tab; don't kill Chrome.
2. **`Runtime.evaluate` WEDGES on the `/vona2/selector/` React+Drift SPA.** Use classic `/vona2/detail/` pages
   only. The selector cards are shadow-DOM/images (no anchors).
3. **Use raw CDP (`data/rawcdp.py`), never Playwright `connect_over_cdp`** (it attaches to Drift iframes/workers
   and hangs ~180 s).
4. **CIRCUIT BREAKER:** on a confirmed 403/Access-Denied, STOP. Recovery = a human re-warms by browsing the
   **homepage** (never a cold deep-link). `data/misumi_fetch.py` has this breaker (`SessionBlocked`).
5. **MSM1 (MISUMI brand) only** has buildable CAD; 3rd-party brands 504/empty.

## Session lifecycle

- Alive check: `GET http://127.0.0.1:9222/json`. Reuse a page target if present.
- No tab? Create one to the HOMEPAGE: `PUT http://127.0.0.1:9222/json/new?https://us.misumi-ec.com/` (re-warm).
- **Health check** (no clicking): in-page POST `cadFormatList` for an owned PN → `{status:200, formatlist:[...]}`
  = WARM; `403`/"access denied" = SESSION_BLOCKED (stop, re-warm).
- Close stale tabs (`GET /json/close/<id>`); piled tabs slow CDP.

## Finding a part / recovering grammar

- **Resolve a detail page with the PN-search redirect, not a stored detailCode** (stored codes go stale →
  PAGE NOT FOUND): `/vona2/result/?Keyword=<PN>&PNSearch=<PN>` redirects to the live `/detail/<seriesCode>/`;
  read the real `seriesCode` from `location.href`.
- **Read specs/drawing with the BARE family/series PN; the FULL configured PN in a /detail/ URL can 404.**
  The family page's **spec TABLE** carries the PN-field breakdown + per-variant callouts. Read table rows via
  `document.querySelectorAll('table tr')` cell text (avoids `<script>` pollution that hits `innerText`).
- **CONSTRUCT the PN from the documented field order + valid codes** — do not fight the React inputs (setting
  `input.value` doesn't commit to React state). Example recovered grammar (FALBS L-bracket):
  `...-L{}-[X]-[H]-{HoleSpec1}-[Y]-[V]-[S]-{HoleSpec2}`; hole codes N/NA = clearance (N3→Ø3.5, NA5→Ø5.5),
  M/MA = tapped, DA = plain through. So `FALBS-SP-T3.2-A80-B30-L30-H40-M4-NA5` = M4-tapped axle + M5-clearance foot.

## Drawings (do this for every part — drawings are truth)

Detail pages expose dimensional drawings as GIFs: `https://us.misumi-ec.com/linked/item/<itemcode>/img/drw_*.gif`
(find via the `img` src list). Fetch with an in-page `fetch()`→base64 (Akamai-friendly), save, convert
`PIL.Image...convert('RGB').save(png)` for VLM viewing. The drawing confirms hole-type (tapped 'M' vs
counterbored) that CAD Ø only hints at.

## CAD fetch

`cadFormatList` → `cadDownload` (brand `MSM1`, `STEP_AP203`; empty `outPutPath` = valid + still building → poll
~8× @ 6 s) → GET the zip → save `cad/<PN>_STEP.zip`. **`rawcdp.Page.evaluate(expr, await_promise=False)` takes
NO args dict** — inline values into the JS string and wrap async as `(async()=>{...})()` with
`await_promise=True`. (NB: `data/misumi_fetch.fetch_cad`'s `evaluate(JS,{dict},...)` call shape is incompatible
with rawcdp — inline instead, or use the Playwright `fetch_misumi_cad`.) Then `cascadio.step_to_glb` (metres),
`trimesh.load(force='scene')` to keep bodies, and MEASURE every mating feature. Print Misumi text
`.encode('ascii','replace')` (cp1252 console).

Related memories: [[misumi-rawcdp-protocol]], [[misumi-cad-handsoff]], [[misumi-thirdparty-no-cad]],
[[misumi-hole-type-codes]], [[catalog-scrapeability]], [[drawings-are-truth]].
