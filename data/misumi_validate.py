"""API-first Misumi discovery: validate many candidate part numbers in ONE cheap
in-page batch, with NO page rendering/screenshots/SPA. cadFormatList(brand,pn) is the
oracle: HTTP 200 + a non-empty formatlist => the PN is VALID *and* has buildable CAD.

This is the fast filter the lead runs before any tab is opened: construct candidate PNs
from a known family grammar, batch-validate, keep the AVAILABLE ones, then fetch_cad.
Reuses the warm session over raw CDP; never launches/relaunches Chrome.
"""
from __future__ import annotations
import json
from data import rawcdp
from data.browse import MISUMI_CAD_BASE


_BATCH_JS = r"""
async ({base, brand, pns}) => {
  const out = {};
  for (const pn of pns) {
    try {
      const r = await fetch(base + "/cadFormatList/", {method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({brandCode:brand, productCode:pn})});
      const txt = await r.text(); let v; try { v = JSON.parse(txt); } catch(e) { v = txt; }
      const fmts = (((v||{}).formatlist)||[]).map(x => x.format);
      out[pn] = {status: r.status, formats: fmts};
    } catch(e) { out[pn] = {status: -1, error: String(e)}; }
  }
  return out;
}
"""


def validate_pns(pns, *, brand="MSM1", port=9222, page_substr="misumi"):
    """Return {pn: {status, formats, STATE}} for each candidate. STATE is AVAILABLE
    (200 + formats), INVALID_PART_NUMBER (200 + empty), SESSION_BLOCKED (401/403), or
    ENDPOINT_ERROR. Run on a LIGHT tab (the homepage) -- detail pages wedge eval."""
    pg = rawcdp.Page(page_substr, port=port)
    try:
        js = (f"(async () => {{ const base='{MISUMI_CAD_BASE}'; const brand='{brand}'; "
              f"const pns={json.dumps(pns)}; return await ({_BATCH_JS})({{base, brand, pns}}); }})()")
        res = pg.evaluate(js, await_promise=True)
        if isinstance(res, str):
            try: res = json.loads(res)
            except Exception: pass
        out = {}
        for pn in pns:
            r = (res or {}).get(pn, {}) if isinstance(res, dict) else {}
            st = r.get("status")
            fmts = r.get("formats") or []
            if st in (401, 403):
                state = "SESSION_BLOCKED"
            elif st == 200 and fmts:
                state = "AVAILABLE"
            elif st == 200:
                state = "INVALID_PART_NUMBER"
            else:
                state = "ENDPOINT_ERROR"
            out[pn] = {"status": st, "formats": fmts, "STATE": state}
        return out
    finally:
        pg.close()


if __name__ == "__main__":
    import sys
    cands = sys.argv[1:]
    for pn, r in validate_pns(cands).items():
        print(f"{r['STATE']:20s} {pn}  formats={r['formats'][:3]}")
