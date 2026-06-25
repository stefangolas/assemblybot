"""One-time interactive McMaster login for the persistent Playwright profile.

Run this YOURSELF (headed) so the automated/headless pipeline stops hitting the
login wall. It opens the same persistent profile the pipeline uses, you log in
by hand, and it waits until a product page loads cleanly, then exits. Cookies
persist in the profile dir, so subsequent headless runs are authenticated.

    python data/login.py
"""
from __future__ import annotations
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

USER_DATA_DIR = Path.home() / ".assemblybot" / "pw-profile"
PROBE = "https://www.mcmaster.com/4575N23/"   # any product page; gated => login wall


def logged_in(page) -> bool:
    page.goto(PROBE, wait_until="networkidle", timeout=60000)
    body = page.inner_text("body").lower()
    return "please log in" not in body and "to continue browsing" not in body


def main():
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(USER_DATA_DIR), headless=False, accept_downloads=True,
            viewport={"width": 1440, "height": 1000})
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://www.mcmaster.com/", wait_until="networkidle", timeout=60000)
        print("\n>>> A browser window opened. Click 'Log in' (top right) and sign in.")
        print(">>> Waiting for the session to clear the login wall (up to 4 min)...\n")
        for i in range(48):                # ~4 min, 5s apart
            time.sleep(5)
            try:
                if logged_in(page):
                    print(">>> Logged in. Session saved to the profile. You can close this.")
                    time.sleep(1); ctx.close(); return
            except Exception:
                pass
            print(f"    still waiting ({(i+1)*5}s)...")
        print(">>> Timed out. Re-run if you didn't finish logging in.")
        ctx.close()


if __name__ == "__main__":
    main()
