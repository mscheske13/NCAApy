from io import StringIO
import io
import time
import random
from playwright.sync_api import sync_playwright

SLEEP_DELAY = 2
_last_used = 0

def random_header() -> dict[str, str]:
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.128 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.128 Mobile Safari/537.36"
    ]
    return {
        "User-Agent": random.choice(user_agents),
        "Referer": "https://stats.ncaa.org/rankings/ranking_summary",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

def get_site(url: str, wait_for_selector: str | None = "body") -> io.StringIO:
    """
    Opens a fresh Playwright Chromium browser for every request.
    Returns the fully rendered page content as StringIO.
    """
    global _last_used

    print(url)

    # Respect minimal delay between requests
    now = time.monotonic()
    if now - _last_used < SLEEP_DELAY:
        time.sleep(SLEEP_DELAY - (now - _last_used))

    headers = random_header()

    with sync_playwright() as p:
        # Always launch a new Chromium instance (headless=False can help with JS/Akamai)
        browser = p.chromium.launch(
            headless=False,
            args=["--window-position=-32000,-32000"]
        )
        context = browser.new_context(
            extra_http_headers={k: v for k, v in headers.items() if k != "User-Agent"},
            user_agent=headers["User-Agent"]
        )
        page = context.new_page()

        # Navigate to the page
        page.goto(url, wait_until="load", timeout=30000)

        # Wait for the page to render fully
        if wait_for_selector:
            try:
                page.wait_for_selector(wait_for_selector, timeout=15000)
            except:
                # fallback wait if selector doesn't appear
                page.wait_for_timeout(5000)
        else:
            page.wait_for_timeout(5000)

        # Get the rendered HTML
        content = page.content()

        # Clean up
        context.close()
        browser.close()

        _last_used = time.monotonic()
        return StringIO(content)

# Example usage
if __name__ == "__main__":
    url = "https://stats.ncaa.org/contests/6388150/box_score"
    html_io = get_site(url)
    print(html_io.read()[:1000])  # print first 1000 characters
