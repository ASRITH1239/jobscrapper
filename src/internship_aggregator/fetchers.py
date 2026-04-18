from __future__ import annotations

from dataclasses import dataclass

import requests

from internship_aggregator.config import (
    DEFAULT_HEADERS,
    PLAYWRIGHT_TIMEOUT_MS,
    REQUEST_TIMEOUT_SECONDS,
)


@dataclass(slots=True)
class PageFetchResult:
    url: str
    html: str
    method: str


class PageFetcher:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def fetch_static(self, url: str) -> PageFetchResult:
        response = self.session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return PageFetchResult(url=str(response.url), html=response.text, method="requests")

    def fetch_dynamic(self, url: str) -> PageFetchResult:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover - depends on runtime setup
            raise RuntimeError(
                "Playwright is not installed. Run `python -m playwright install chromium`."
            ) from exc

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=PLAYWRIGHT_TIMEOUT_MS)
            html = page.content()
            resolved_url = page.url
            browser.close()
        return PageFetchResult(url=resolved_url, html=html, method="playwright")

