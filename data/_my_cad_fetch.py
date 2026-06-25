"""fetch_cad pinned to a specific known target id (avoid substring tab collisions
with other concurrently-running scouts sharing the same warm Chrome)."""
from __future__ import annotations

import base64
import json
import time
from pathlib import Path

from data._my_tab import PageById
from data.browse import MISUMI_CAD_BASE, _MISUMI_FETCH_JS

ROOT = Path(__file__).resolve().parent.parent
CAD = ROOT / "cad"


class SessionBlocked(Exception):
    pass


class CadUnavailable(Exception):
    pass


def _looks_blocked(res):
    fl = (res or {}).get("fl") or {}
    if fl.get("status") in (401, 403):
        return True
    body = fl.get("body")
    return isinstance(body, str) and "access denied" in body.lower()


def fetch_cad_pinned(target_id: str, part_number: str, *, brand="MSM1", fmt="STEP_AP203",
                      port=9222, dest_dir=CAD, build_polls=8, backoff_s=6.0) -> Path:
    pg = PageById(target_id, port=port)
    last = None
    for attempt in range(build_polls):
        js_inlined = (f"(async () => {{ const base='{MISUMI_CAD_BASE}'; "
                      f"const brand='{brand}'; const pn='{part_number}'; const fmt='{fmt}'; "
                      f"return await ({_MISUMI_FETCH_JS})({{base, brand, pn, fmt}}); }})()")
        res = pg.evaluate(js_inlined, await_promise=True)
        if isinstance(res, str):
            try:
                res = json.loads(res)
            except Exception:
                pass
        last = res
        if _looks_blocked(res):
            raise SessionBlocked(f"{part_number}: session 403/login-walled -- STOP, do not retry.")
        if res and res.get("b64"):
            dest = Path(dest_dir)
            dest.mkdir(parents=True, exist_ok=True)
            out = dest / f"{part_number.replace('/', '_')}_STEP.zip"
            out.write_bytes(base64.b64decode(res["b64"]))
            print(f"[misumi] {part_number}: {res['size']} bytes ({res.get('used')}) -> {out}")
            return out
        if res and res.get("error") == "no outPutPath":
            time.sleep(backoff_s)
            continue
        raise CadUnavailable(f"{part_number}: {res}")
    raise CadUnavailable(f"{part_number}: CAD never finished building ({last})")
