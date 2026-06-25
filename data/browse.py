"""The data layer: Playwright driving mcmaster.com (Section 3).

NO API, EVER. A single authenticated persistent browser context is the only
data path: it navigates the catalog, screenshots pages for the VLM to read,
and drives the CAD-download widget. A plain HTTP GET returns only a
"please enable JavaScript" shell (Akamai gates non-browser requests), so a
real browser is mandatory.

Selectors are used ONLY to operate controls (category links, filter toggles,
the CAD-download button) -- never to read data. Every value that ends up in a
library entry is read by the VLM off a screenshot, so selector drift can break
a click but can never corrupt an extracted value.

Throttle, vary pacing, cache aggressively, browse once. This is automated
access to someone else's site under their T&C -- stay conservative. Discovery
and retrieval happen here in Phase 2 only; all assembly reasoning (Phases 3-4)
runs offline against the cached library.
"""
from __future__ import annotations

import random
import time
from contextlib import contextmanager
from pathlib import Path

USER_DATA_DIR = Path.home() / ".assemblybot" / "pw-profile"
DOWNLOAD_DIR = Path(__file__).resolve().parent.parent / "cad"


def _polite_pause(lo: float = 1.5, hi: float = 4.0) -> None:
    """Throttle with varied pacing -- courteous-guest behaviour."""
    time.sleep(random.uniform(lo, hi))


@contextmanager
def session(headless: bool = False):
    """One authenticated persistent context, reused across all parts in a run.
    Sign in once (manually, headed) if CAD downloads require it; the profile
    dir persists the session."""
    from playwright.sync_api import sync_playwright

    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(USER_DATA_DIR),
            headless=headless,
            accept_downloads=True,
            viewport={"width": 1440, "height": 1600},
        )
        try:
            yield ctx
        finally:
            ctx.close()


def open_product(ctx, part_number: str):
    """Navigate to a product page and wait on network-idle (never a fixed sleep
    for load -- the polite pause is separate, for pacing)."""
    page = ctx.new_page()
    url = f"https://www.mcmaster.com/{part_number}/"
    page.goto(url, wait_until="networkidle", timeout=60000)
    return page, url


def screenshot_product(page, out_path: str) -> str:
    """Full-page screenshot for the VLM to read the spec table + drawing.
    Returns the path; the VLM (this agent) reads it via the Read tool."""
    page.screenshot(path=out_path, full_page=True)
    return out_path


# The CAD widget is a combobox (aria-label "Select CAD file type") whose
# options are the offered formats, plus a sibling <a download> whose href the
# combobox rewrites per selection. No sign-in is required. Prefer the
# simplified, non-threaded 3-D variant for mating (threads are a role, not
# geometry); always also grab the 2-D DWG -- it is the feature-geometry
# authority (Section 3). Option labels are verbatim from the live widget.
CAD_FORMATS = {
    "step": "3-D STEP no threads",   # simplified, non-threaded -- preferred
    "step_full": "3-D STEP",
    "parasolid": "3-D Parasolid no threads",
    "dwg": "2-D DWG",                # the geometry authority
    "pdf2d": "2-D PDF",
}


def download_cad(ctx, page, part_number: str, kind: str = "step",
                 ext: str | None = None) -> tuple[str, str] | None:
    """Drive the CAD-download widget via accessible-role locators (operating
    controls only -- never to read data). `kind` selects a CAD_FORMATS entry.
    Returns (saved_path, source_href) or None if the widget could not be driven.
    """
    option_label = CAD_FORMATS.get(kind, kind)
    ext = ext or kind.replace("_full", "")
    try:
        combo = page.get_by_role("combobox", name="Select CAD file type")
        combo.scroll_into_view_if_needed(timeout=8000)
        combo.click(timeout=8000)
        page.get_by_role("option", name=option_label, exact=True).click(timeout=8000)
        anchor = page.locator("a[download]").first
        href = anchor.get_attribute("href")
        with page.expect_download(timeout=45000) as dl_info:
            anchor.locator("button").click(timeout=8000)
        dl = dl_info.value
        dest = DOWNLOAD_DIR / f"{part_number}.{ext}"
        dl.save_as(str(dest))
        _polite_pause()
        return str(dest), href
    except Exception as e:  # noqa: BLE001 -- best-effort widget operation
        print(f"[browse] CAD '{option_label}' for {part_number} failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Misumi CAD: HANDS-OFF replay of the download flow (decoded from a captured
# manual run -- see data/capture_misumi.py + out/misumi_capture.log).
#
# The "Generate" button fires no modal under scripted clicks, but the underlying
# flow is just two authenticated POSTs (cookies carry the login) + one GET:
#   1) POST /vona2/pc/system/api/cadFormatList/  {brandCode, productCode}
#        -> {"formatlist":[{"format":"STEP_AP203",...}, ...]}
#   2) POST /vona2/pc/system/api/cadDownload/    {brandCode, productCode,
#        formatType, userId}  -> {"status":"1","outPutPath":"https://rd-jp-
#        caddata.misumi-ec.com/.../<PN>_STEP.zip"}   (blocks ~5s while it builds)
#   3) GET  <outPutPath>  -> the STEP zip
# No sessionId needed for (1)/(2); auth is the session cookie on us.misumi-ec.com.
# Run it on a page from the authenticated CDP browser (b.contexts[0].pages[0]).
MISUMI_CAD_BASE = "https://us.misumi-ec.com/vona2/pc/system/api"


def misumi_user_id(page) -> str | None:
    """Read the logged-in Misumi user code off the page (the value the manual
    flow puts in cadDownload.userId). Falls back to None if not signed in."""
    try:
        uid = page.evaluate(
            "() => window.__NEXT_DATA__?.props?.pageProps?.userInfo?.userCode "
            "|| document.cookie.match(/userCode=([0-9]+)/)?.[1] || null")
        return uid
    except Exception:
        return None


_MISUMI_FETCH_JS = r"""
async ({base, brand, pn, fmt}) => {
  const j = async (path, body) => {
    const r = await fetch(base + path, {method:"POST",
      headers:{"Content-Type":"application/json"}, body: JSON.stringify(body)});
    const txt=await r.text(); let v; try{ v=JSON.parse(txt); }catch(e){ v=txt; }  // read body ONCE (avoid 'body stream already read')
    return {status:r.status, body:v};
  };
  // (1) which formats exist (also confirms auth on this endpoint)
  const fl = await j("/cadFormatList/", {brandCode:brand, productCode:pn});
  const formats = ((fl.body||{}).formatlist||[]).map(x=>x.format);
  let use = formats.includes(fmt) ? fmt
            : (formats.find(x=>x.startsWith("STEP")) || formats[0]);
  if(!use) return {error:"no formats", fl};
  // (2) generate -> outPutPath (server builds the CAD, ~5s; fetch blocks on it)
  const gen = await j("/cadDownload/",
      {brandCode:brand, productCode:pn, formatType:use, userId:""});
  const url = (gen.body||{}).outPutPath;
  if((gen.body||{}).status!=="1" || !url)
    return {error:"no outPutPath", gen, used:use};
  // (3) fetch the zip bytes as base64 (in-page fetch == Akamai-friendly)
  const r = await fetch(url);
  if(!r.ok) return {error:"file "+r.status, url};
  const buf = new Uint8Array(await r.arrayBuffer());
  let bin=""; const CH=0x8000;
  for(let i=0;i<buf.length;i+=CH) bin+=String.fromCharCode.apply(null, buf.subarray(i,i+CH));
  return {url, used:use, b64: btoa(bin), size: buf.length};
}
"""


def fetch_misumi_cad(page, product_code: str, *, user_id: str = "",
                     brand="MSM1", fmt="STEP_AP203", dest_dir=None) -> tuple[str, str] | None:
    """Hands-off: pull the STEP zip for a (configured) Misumi part number with NO
    clicking. The flow runs as in-page fetch() so Akamai sees a genuine browser
    request (an out-of-page request context gets 403 on cadDownload). Auth is the
    session cookie -- `page` must be from the signed-in CDP browser. `user_id` is
    unused now (the server keys off the session) but kept for call-site clarity.
    Returns (saved_zip_path, file_url) or None."""
    import base64
    dest_dir = Path(dest_dir) if dest_dir else DOWNLOAD_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    res = page.evaluate(_MISUMI_FETCH_JS,
                        {"base": MISUMI_CAD_BASE, "brand": brand,
                         "pn": product_code, "fmt": fmt})
    if not res or res.get("error"):
        print(f"[misumi] {product_code} fetch failed: {res}")
        return None
    safe = product_code.replace("/", "_")
    dest = dest_dir / f"{safe}_STEP.zip"
    dest.write_bytes(base64.b64decode(res["b64"]))
    _polite_pause()
    print(f"[misumi] {product_code}: {res['size']} bytes ({res['used']}) -> {dest}")
    return str(dest), res["url"]
