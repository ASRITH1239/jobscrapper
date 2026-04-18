from __future__ import annotations

from bs4 import BeautifulSoup

from internship_aggregator.extractors import extract_generic_jobs, extract_json_ld_jobs
from internship_aggregator.fetchers import PageFetcher
from internship_aggregator.models import CompanyTarget, JobRecord, ScrapeFailure, ScrapeResult
from internship_aggregator.sources.base import BaseSourceScraper
from internship_aggregator.utils import dedupe_hash, should_use_dynamic_fetch, utc_now_iso


class CareerPageScraper(BaseSourceScraper):
    def __init__(self, fetcher: PageFetcher, *, skip_dynamic: bool = False) -> None:
        self.fetcher = fetcher
        self.skip_dynamic = skip_dynamic

    def matches(self, company: CompanyTarget) -> bool:
        return True

    def scrape(self, company: CompanyTarget) -> ScrapeResult:
        try:
            fetched = self.fetcher.fetch_static(company.career_page_url)
        except Exception as exc:
            if self.skip_dynamic:
                return ScrapeResult(
                    failures=[
                        ScrapeFailure(
                            company=company.company,
                            url=company.career_page_url,
                            reason=f"Static fetch failed: {exc}",
                        )
                    ]
                )
            fetched = None

        jobs: list[JobRecord] = []
        failure_reason: str | None = None

        if fetched:
            jobs = self._extract_jobs(company, fetched.html, fetched.url)

        if not jobs and not self.skip_dynamic and (
            company.dynamic or should_use_dynamic_fetch(company.career_page_url)
        ):
            try:
                fetched = self.fetcher.fetch_dynamic(company.career_page_url)
                jobs = self._extract_jobs(company, fetched.html, fetched.url)
            except Exception as exc:
                failure_reason = f"Dynamic fetch failed: {exc}"
        elif fetched is None:
            failure_reason = "No HTML returned"

        failures = []
        if not jobs and failure_reason:
            failures.append(
                ScrapeFailure(
                    company=company.company,
                    url=company.career_page_url,
                    reason=failure_reason,
                )
            )
        return ScrapeResult(jobs=jobs, failures=failures)

    def _extract_jobs(self, company: CompanyTarget, html: str, page_url: str) -> list[JobRecord]:
        soup = BeautifulSoup(html, "html.parser")
        discovered = extract_json_ld_jobs(soup, company, page_url)
        if not discovered:
            discovered = extract_generic_jobs(soup, company, page_url)

        scraped_at = utc_now_iso()
        jobs: list[JobRecord] = []
        for raw_job in discovered:
            if not raw_job["apply_link"]:
                continue
            jobs.append(
                JobRecord(
                    id=dedupe_hash(raw_job["title"], company.company, raw_job["apply_link"]),
                    title=raw_job["title"],
                    company=company.company,
                    location=raw_job["location"] or "Not specified",
                    apply_link=raw_job["apply_link"],
                    category=company.category,
                    type=company.type,
                    source=raw_job["source"] or company.source,
                    posted_at=raw_job.get("posted_at"),
                    scraped_at=scraped_at,
                    first_seen_at=scraped_at,
                    last_seen_at=scraped_at,
                    discovered_via=raw_job.get("discovered_via"),
                )
            )
        return jobs
