from __future__ import annotations

from urllib.parse import urlparse

from bs4 import BeautifulSoup

from internship_aggregator.fetchers import PageFetcher
from internship_aggregator.models import CompanyTarget, JobRecord, ScrapeFailure, ScrapeResult
from internship_aggregator.sources.base import BaseSourceScraper
from internship_aggregator.utils import dedupe_hash, normalize_text, normalize_url, utc_now_iso


class JobBoardScraper(BaseSourceScraper):
    def __init__(self, fetcher: PageFetcher, *, skip_dynamic: bool = False) -> None:
        self.fetcher = fetcher
        self.skip_dynamic = skip_dynamic

    def matches(self, company: CompanyTarget) -> bool:
        host = urlparse(company.career_page_url).netloc.lower()
        return any(domain in host for domain in ("linkedin.com", "indeed.", "internshala.com"))

    def scrape(self, company: CompanyTarget) -> ScrapeResult:
        try:
            fetched = self.fetcher.fetch_static(company.career_page_url)
        except Exception:
            if self.skip_dynamic:
                return ScrapeResult(
                    failures=[
                        ScrapeFailure(
                            company=company.company,
                            url=company.career_page_url,
                            reason="Job board fetch failed",
                        )
                    ]
                )
            fetched = self.fetcher.fetch_dynamic(company.career_page_url)

        soup = BeautifulSoup(fetched.html, "html.parser")
        host = urlparse(fetched.url).netloc.lower()

        if "linkedin.com" in host:
            raw_jobs = self._extract_linkedin(soup, fetched.url)
        elif "indeed." in host:
            raw_jobs = self._extract_indeed(soup, fetched.url)
        else:
            raw_jobs = self._extract_internshala(soup, fetched.url)

        unique_jobs: dict[tuple[str, str], dict[str, str]] = {}
        for job in raw_jobs:
            key = (job["title"].lower(), job["apply_link"].lower())
            unique_jobs.setdefault(key, job)

        scraped_at = utc_now_iso()
        jobs = [
            JobRecord(
                id=dedupe_hash(job["title"], company.company, job["apply_link"]),
                title=job["title"],
                company=company.company,
                location=job["location"],
                apply_link=job["apply_link"],
                category=company.category,
                type=company.type,
                source=job["source"],
                posted_at=None,
                scraped_at=scraped_at,
                first_seen_at=scraped_at,
                last_seen_at=scraped_at,
                discovered_via=job["discovered_via"],
            )
            for job in unique_jobs.values()
        ]
        return ScrapeResult(jobs=jobs)

    def _extract_linkedin(self, soup: BeautifulSoup, page_url: str) -> list[dict[str, str]]:
        jobs: list[dict[str, str]] = []
        url_implies_internship = self._url_implies_internship(page_url)
        for card in soup.select("li div.base-search-card, div.base-card, li.jobs-search-results__list-item"):
            title_node = card.select_one("h3, .base-search-card__title, .job-search-card__title")
            link_node = card.select_one("a[href]")
            location_node = card.select_one(".job-search-card__location, .job-search-card__listdate")
            title = normalize_text(title_node.get_text(" ", strip=True) if title_node else "")
            if not url_implies_internship and "intern" not in title.lower() and "trainee" not in title.lower():
                continue
            apply_link = normalize_url(link_node.get("href") if link_node else "", page_url)
            jobs.append(
                {
                    "title": title,
                    "location": normalize_text(location_node.get_text(" ", strip=True) if location_node else "")
                    or "Not specified",
                    "apply_link": apply_link,
                    "source": "linkedin",
                    "discovered_via": "linkedin-board",
                }
            )
        return jobs

    def _extract_indeed(self, soup: BeautifulSoup, page_url: str) -> list[dict[str, str]]:
        jobs: list[dict[str, str]] = []
        url_implies_internship = self._url_implies_internship(page_url)
        for card in soup.select("div.job_seen_beacon, div.slider_container .slider_item, div[data-testid='slider_item']"):
            title_node = card.select_one("h2 a, a.jcs-JobTitle")
            location_node = card.select_one("[data-testid='text-location'], div.company_location")
            title = normalize_text(title_node.get_text(" ", strip=True) if title_node else "")
            if not url_implies_internship and "intern" not in title.lower() and "trainee" not in title.lower():
                continue
            apply_link = normalize_url(title_node.get("href") if title_node else "", page_url)
            jobs.append(
                {
                    "title": title,
                    "location": normalize_text(location_node.get_text(" ", strip=True) if location_node else "")
                    or "Not specified",
                    "apply_link": apply_link,
                    "source": "indeed",
                    "discovered_via": "indeed-board",
                }
            )
        return jobs

    def _extract_internshala(self, soup: BeautifulSoup, page_url: str) -> list[dict[str, str]]:
        jobs: list[dict[str, str]] = []
        url_implies_internship = self._url_implies_internship(page_url)
        for card in soup.select("div.individual_internship, div.internship_meta"):
            title_node = card.select_one("a.job-title-href, h3 a, .job-internship-name a")
            location_node = card.select_one(".locations, .location_names, .row-1-item.locations")
            title = normalize_text(title_node.get_text(" ", strip=True) if title_node else "")
            if not url_implies_internship and "intern" not in title.lower() and "trainee" not in title.lower():
                continue
            apply_link = normalize_url(title_node.get("href") if title_node else "", page_url)
            jobs.append(
                {
                    "title": title,
                    "location": normalize_text(location_node.get_text(" ", strip=True) if location_node else "")
                    or "Not specified",
                    "apply_link": apply_link,
                    "source": "internshala",
                    "discovered_via": "internshala-board",
                }
            )
        return jobs

    def _url_implies_internship(self, page_url: str) -> bool:
        lower = page_url.lower()
        return any(keyword in lower for keyword in ("intern", "internship", "trainee"))
