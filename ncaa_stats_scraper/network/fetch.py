import io
import time
import random
import threading
from contextlib import contextmanager
from playwright.sync_api import sync_playwright, Browser, Page

SLEEP_DELAY = 2.0
_last_used = 0.0
_lock = threading.Lock()   # guard _last_used for threads
CONCURRENT_SEMAPHORE = threading.Semaphore(2)  # allow up to 2 parallel pages

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.128 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.128 Mobile Safari/537.36"
]

def random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": random.choice([
            "https://stats.ncaa.org/rankings/ranking_summary",
            "https://google.com/",
            "https://bing.com/"
        ]),
        "Accept-Language": random.choice(["en-US,en;q=0.9", "en-GB,en;q=0.9", "en;q=0.8"]),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

class BrowserManager:
    def __init__(self):
        self._p = None
        self._browser: Browser | None = None
        self._last_used = 0.0
        self._lock = threading.Lock()
        self._shutdown_thread = None
        self.BROWSER_IDLE_TIMEOUT = 10  # seconds

    def start(self):
        with self._lock:
            if self._p is None:
                self._p = sync_playwright().start()
                self._browser = self._p.chromium.launch(
                    headless=False,
                    args=["--no-sandbox", "--window-position=-32000,-32000"]
                )
                # start idle monitor
                self._shutdown_thread = threading.Thread(
                    target=self._idle_monitor, daemon=True
                )
                self._shutdown_thread.start()
            self._last_used = time.monotonic()
            return self._browser

    def _idle_monitor(self):
        """Background thread to close browser after inactivity."""
        while True:
            time.sleep(1)
            with self._lock:
                if self._browser and (time.monotonic() - self._last_used) > self.BROWSER_IDLE_TIMEOUT:
                    print("[BrowserManager] Closing idle browser...")
                    try:
                        self._browser.close()
                    except Exception:
                        pass
                    self._browser = None
                    try:
                        self._p.stop()
                    except Exception:
                        pass
                    self._p = None
                    return  # exit thread once closed

    def stop(self):
        with self._lock:
            if self._browser:
                try:
                    self._browser.close()
                except Exception:
                    pass
                self._browser = None
            if self._p:
                try:
                    self._p.stop()
                except Exception:
                    pass
                self._p = None

    @contextmanager
    def new_page(self, proxy: dict | None = None, headers: dict | None = None):
        browser = self.start()  # ensures browser is live or launches new one
        ctx = browser.new_context(
            user_agent=headers.get("User-Agent") if headers else None,
            extra_http_headers={k: v for k, v in (headers or {}).items() if k != "User-Agent"},
            viewport={"width": 1280, "height": 800}
        )
        page: Page = ctx.new_page()
        try:
            yield page
        finally:
            ctx.close()
            with self._lock:
                self._last_used = time.monotonic()


# single manager instance (reuse across calls)
_MANAGER = BrowserManager()

def polite_wait():
    global _last_used
    with _lock:
        now = time.monotonic()
        delay = random.uniform(SLEEP_DELAY, SLEEP_DELAY * 2.0)  # jitter
        if now - _last_used < delay:
            to_sleep = delay - (now - _last_used)
            time.sleep(to_sleep)
        _last_used = time.monotonic()

def get_site(url: str, wait_for_selector: str | None = "body", max_retries=3) -> io.StringIO:
    # throttle concurrency

    print(url)
    with CONCURRENT_SEMAPHORE:
        headers = random_headers()
        polite_wait()
    

        attempt = 0
        backoff = 1.0
        while attempt < max_retries:
            attempt += 1
            try:
                with _MANAGER.new_page(headers=headers) as page:
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)

                    # small human-like behavior
                    try:
                        page.set_viewport_size({"width": 1280, "height": 800})
                    except Exception:
                        pass
                    # a small scroll
                    try:
                        page.mouse.wheel(0, 100)
                        time.sleep(random.uniform(0.1, 0.5))
                    except Exception:
                        pass

                    if wait_for_selector:
                        try:
                            page.wait_for_selector(wait_for_selector, timeout=15000)
                        except Exception:
                            # fallback, don't fail hard
                            page.wait_for_timeout(2000)

                    content = page.content()
                    with _lock:
                        _last_used = time.monotonic()
                    return io.StringIO(content)

            except Exception as e:
                # detect common server-side blocks and back off
                # log for debugging
                print(f"[get_site] attempt {attempt} failed: {e}")
                time.sleep(backoff + random.random() * backoff)
                backoff *= 2.0
                # if you see a status here like 429 or frequent timeouts, stop or rotate proxies
        raise RuntimeError(f"Failed to fetch {url} after {max_retries} attempts")
