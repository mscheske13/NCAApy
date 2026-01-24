import io
import time
import random
import threading
from contextlib import contextmanager
from playwright.sync_api import sync_playwright, Browser, Page

SLEEP_DELAY = 2.0

import random

class ScrapingUsageNotAcknowledged(Exception):
    def __init__(self):
        self.message = (
            "Warning: Using this on a private or restricted network may lead to a permanent ban "
            "from the NCAA stats database.\n\n"
            "Any major scraping projects should be done on a major public network or with rotating "
            "proxies.\n\n"
            "Using this outside stats.ncaa.org should be safe.\n\n"
            "If you accept the risks, disable this warning in get_site() by passing in acknowledgement=True"
        )

    def __str__(self):
        return self.message


USER_AGENTS = [
    # Windows Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.128 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6320.59 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.5999.80 Safari/537.36",

    # Windows Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",

    # macOS Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",

    # Android Chrome
    "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.128 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-G998U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6320.59 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; Redmi Note 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.5999.80 Mobile Safari/537.36",
]

REFERERS = [
    "https://google.com",
    "https://bing.com",
    "https://duckduckgo.com",
    "https://yahoo.com",
    "https://stats.ncaa.org",
    "https://facebook.com",
    "https://twitter.com",
    "https://reddit.com",
    "https://espn.com",
]

ACCEPT_LANG = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
    "en;q=0.8",
    "en-US;q=0.7,en;q=0.3",
    "en-CA,en;q=0.9",
    "en-AU,en;q=0.9",
    "en-ZA,en;q=0.8",
    "en-NZ,en;q=0.9",
]

ACCEPT_HEADERS = [
    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "text/html,application/xml;q=0.9,*/*;q=0.8",
    "application/json,text/html;q=0.9,*/*;q=0.8",
    "text/html,*/*;q=0.8",
    "application/xhtml+xml,text/html;q=0.9,*/*;q=0.8",
    "application/xml,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "text/html;q=0.9,application/xml;q=0.8,*/*;q=0.7",
    "text/plain,text/html;q=0.9,*/*;q=0.8",
    "application/json;q=0.9,text/html;q=0.8,*/*;q=0.7",
    "image/avif,image/webp,image/apng,*/*;q=0.8",
    "application/*;q=0.9,text/*;q=0.8,*/*;q=0.7",
    "*/*;q=0.8",
]

def random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": random.choice(REFERERS),
        "Accept-Language": random.choice(ACCEPT_LANG),
        "Accept": random.choice(ACCEPT_HEADERS),
    }

import io
import time
import random
from playwright.sync_api import sync_playwright

SLEEP_DELAY = 2.0

def random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": random.choice(REFERERS),
        "Accept-Language": random.choice(ACCEPT_LANG),
        "Accept": random.choice(ACCEPT_HEADERS),
    }


def get_site(url: str, acknowledgement: bool = False) -> io.StringIO:

    if not acknowledgement:
        raise ScrapingUsageNotAcknowledged()

    time.sleep(2 + random.random())

    print(url)

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        page = browser.new_page(extra_http_headers=random_headers())

        page.goto(url, timeout=60000, wait_until="load")

        html = page.content()

        browser.close()

    return io.StringIO(html)
