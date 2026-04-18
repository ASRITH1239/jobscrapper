from __future__ import annotations

import json
from dataclasses import asdict
from datetime import timedelta
from pathlib import Path

from internship_aggregator.config import STALE_JOB_RETENTION_DAYS
from internship_aggregator.fetchers import PageFetcher
from internship_aggregator.models import CompanyTarget, JobRecord
from internship_aggregator.sources.career_page import CareerPageScraper
from internship_aggregator.sources.job_boards import JobBoardScraper
from internship_aggregator.utils import is_new_within_24h, parse_datetime, utc_now, utc_now_iso


def load_companies(path: Path) -> list[CompanyTarget]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    return [CompanyTarget.from_dict(item) for item in payload]


def load_existing_jobs(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    jobs = payload.get("jobs", payload if isinstance(payload, list) else [])
    return {job["id"]: job for job in jobs}


def run_pipeline(
    companies: list[CompanyTarget],
    *,
    existing_jobs_path: Path,
    skip_dynamic: bool = False,
    limit: int | None = None,
) -> dict:
    if limit is not None:
        companies = companies[:limit]

    fetcher = PageFetcher()
    scrapers = [
        JobBoardScraper(fetcher, skip_dynamic=skip_dynamic),
        CareerPageScraper(fetcher, skip_dynamic=skip_dynamic),
    ]

    existing_jobs = load_existing_jobs(existing_jobs_path)
    now = utc_now()
    now_iso = now.isoformat()
    fresh_jobs: dict[str, dict] = {}
    failures: list[dict] = []
    scraped_companies = 0

    for company in companies:
        scraper = next((candidate for candidate in scrapers if candidate.matches(company)), scrapers[-1])
        result = scraper.scrape(company)
        if result.jobs:
            scraped_companies += 1
        for failure in result.failures:
            failures.append(asdict(failure))
        for job in result.jobs:
            previous = existing_jobs.get(job.id)
            if previous:
                job.first_seen_at = previous.get("first_seen_at", job.first_seen_at)
            job.last_seen_at = now_iso
            job.scraped_at = now_iso
            fresh_jobs[job.id] = job.to_dict()

    retention_cutoff = now - timedelta(days=STALE_JOB_RETENTION_DAYS)
    for job_id, previous in existing_jobs.items():
        if job_id in fresh_jobs:
            continue
        last_seen = parse_datetime(previous.get("last_seen_at"))
        if last_seen and last_seen >= retention_cutoff:
            fresh_jobs[job_id] = previous

    ordered_jobs = sorted(
        fresh_jobs.values(),
        key=lambda job: (
            parse_datetime(job.get("first_seen_at")) or now,
            parse_datetime(job.get("posted_at")) or now,
        ),
        reverse=True,
    )

    return {
        "generated_at": now_iso,
        "stats": {
            "total_companies": len(companies),
            "scraped_companies": scraped_companies,
            "total_jobs": len(ordered_jobs),
            "new_jobs_last_24h": sum(is_new_within_24h(job.get("first_seen_at"), now) for job in ordered_jobs),
            "failures": len(failures),
        },
        "jobs": ordered_jobs,
        "failures": failures,
    }
