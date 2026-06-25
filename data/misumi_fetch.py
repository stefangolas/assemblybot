"""Disciplined Misumi CAD fetch -- the judicious takeaway from the catalog-access
architecture, minus the full provider/cache framework.

Today's failure was self-inflicted: I scraped the heavy `/vona2/selector/` SPA,
then KILLED+RELAUNCHED Chrome to recover wedged tabs, which stripped the warm
Akamai sensor cookie and got the whole instance 403'd site-wide (which also kills
the CAD fetch, since it rides the same session). This module bakes in the rules
that prevent that:

  * REUSE the already-warm tab over raw CDP -- never launch/relaunch a profile here.
  * Use the STRUCTURED endpoint (the proven in-page `cadFormatList`/`cadDownload`
    fetch), not DOM/clicks/screenshots.
  * CIRCUIT BREAKER: a 403 / "Access Denied" session raises `SessionBlocked` and
    STOPS -- it never loops on a denied page (that is what deepens an Akamai flag).
    Recovery is a human re-warming the session (browse Misumi once in that tab),
    not an automated retry.
  * The ONLY legitimate retry is CAD-still-building (`outPutPath` empty) -- bounded
    polling with backoff.

Reach a configured part by its full part number; reach the part number itself from
a classic `/vona2/detail/<series>/` page (read the PN template + construct it) --
NOT the React selector. See the FAST PART-FETCH PROTOCOL in CLAUDE.md.
"""
from __future__ import annotations

import base64
import time
from pathlib import Path

from data import rawcdp
from data.browse import MISUMI_CAD_BASE, _MISUMI_FETCH_JS

ROOT = Path(__file__).resolve().parent.parent
CAD = ROOT / "cad"


class SessionBlocked(Exception):
    """The Misumi session is 403'd / login-walled. Do NOT retry -- re-warm it."""


class CadUnavailable(Exception):
    """The part number is valid-but-no-CAD, or the build never completed."""


def _looks_blocked(res: dict) -> bool:
    """Detect an Akamai/login block from the structured fetch result instead of
    scraping a page: cadFormatList came back 403 or as an HTML 'Access Denied'."""
    fl = (res or {}).get("fl") or {}
    if fl.get("status") in (401, 403):
        return True
    body = fl.get("body")
    return isinstance(body, str) and "access denied" in body.lower()


def fetch_cad(part_number: str, *, brand: str = "MSM1", fmt: str = "STEP_AP203",
              port: int = 9222, dest_dir: Path | str = CAD,
              build_polls: int = 8, backoff_s: float = 6.0) -> Path:
    """Pull the STEP zip for a configured Misumi PN through the warm CDP tab.

    Raises `SessionBlocked` (stop + re-warm) or `CadUnavailable`. Returns the zip
    path on success. Never launches Chrome -- it attaches to the existing tab."""
    pg = rawcdp.Page("misumi", port=port)            # reuse warm session; no launch
    try:
        last = None
        for attempt in range(build_polls):
            # wrap the arrow-fn in an async IIFE that CALLS it -- otherwise
            # Runtime.evaluate returns the uncalled function object (serializes to {}).
            js_inlined = (f"(async () => {{ const base='{MISUMI_CAD_BASE}'; "
                          f"const brand='{brand}'; const pn='{part_number}'; const fmt='{fmt}'; "
                          f"return await ({_MISUMI_FETCH_JS})({{base, brand, pn, fmt}}); }})()")
            res = pg.evaluate(js_inlined, await_promise=True)
            import json
            if isinstance(res, str):
                try: res = json.loads(res)
                except: pass
            last = res
            if _looks_blocked(res):
                raise SessionBlocked(
                    f"{part_number}: session is 403/login-walled -- re-warm Misumi "
                    f"in the tab (browse once), do NOT relaunch. Aborting (no retry).")
            if res and res.get("b64"):
                dest = Path(dest_dir); dest.mkdir(parents=True, exist_ok=True)
                out = dest / f"{part_number.replace('/', '_')}_STEP.zip"
                out.write_bytes(base64.b64decode(res["b64"]))
                print(f"[misumi] {part_number}: {res['size']} bytes "
                      f"({res.get('used')}) -> {out}")
                return out
            # the one legitimate retry: server still building the CAD
            if res and res.get("error") == "no outPutPath":
                time.sleep(backoff_s)
                continue
            # valid PN but genuinely no buildable CAD, or an unexpected shape
            raise CadUnavailable(f"{part_number}: {res}")
        raise CadUnavailable(f"{part_number}: CAD never finished building ({last})")
    finally:
        pg.close()
