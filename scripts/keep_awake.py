"""Open the live site in a headless browser so Streamlit Community Cloud doesn't put it to sleep.

If the app has already gone to sleep, click the wake-up button and wait for it to start.
Run by .github/workflows/keep-awake.yml every few hours. Needs: pip install playwright && playwright install chromium
"""
import re
import sys

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

URL = "https://9thstreetmarket.streamlit.app/"
WAKE_BUTTON = r"get this app back up"


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=90_000)
        page.wait_for_timeout(8_000)

        wake = page.get_by_role("button", name=re.compile(WAKE_BUTTON, re.I))
        if wake.count():
            print("App was asleep, waking it up")
            wake.click()
            page.wait_for_timeout(5_000)

        # The app itself runs inside an iframe; wait until its first page has drawn something.
        app = page.frame_locator("iframe[title='streamlitApp']")
        try:
            app.locator("[data-testid='stApp']").wait_for(timeout=180_000)
            app.locator("h1, h2, h3").first.wait_for(timeout=120_000)
        except PlaywrightTimeout:
            print("App did not finish loading in time")
            browser.close()
            return 1
        print("App is awake:", page.title())
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
