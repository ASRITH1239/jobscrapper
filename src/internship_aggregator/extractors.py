from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from bs4 import BeautifulSoup

from internship_aggregator.config import MAX_JOBS_PER_COMPANY
from internship_aggregator.models import CompanyTarget
from internship_aggregator.utils import (
    guess_location,
    is_internship_title,
    normalize_text,
    normalize_title,
    normalize_url,
    safe_json_loads,
)


def _iter_json_nodes(payload: Any) -> Iterable[dict[str, Any]]:
    if isinstance(payload, dict):
        yield payload
        for value in payload.values():
            yield from _iter_json_nodes(value)
    elif isinstance(payload, list):
        for item in payload:
            yield from _iter_json_nodes(item)


def extract_json_ld_jobs(
    soup: BeautifulSoup,
    company: CompanyTarget,
    page_url: str,
) -> list[dict[str, str | None]]:
    jobs: list[dict[str, str | None]] = []
    for script in soup.find_all("script", attrs={"type": lambda value: value and "ld+json" in value}):
        raw_text = script.string or script.get_text(strip=True)
        if not raw_text:
            continue
        try:
            payload = safe_json_loads(raw_text)
        except Exception:
            continue

        for node in _iter_json_nodes(payload):
            node_type = node.get("@type")
            if isinstance(node_type, list):
                is_job_posting = "JobPosting" in node_type
            else:
                is_job_posting = node_type == "JobPosting"
            if not is_job_posting:
                continue

            title = normalize_title(node.get("title"))
            if not is_internship_title(title):
                continue

            location_value = node.get("jobLocation") or node.get("applicantLocationRequirements")
            location = "Not specified"
            if isinstance(location_value, dict):
                address = location_value.get("address", {})
                location = normalize_text(
                    address.get("addressLocality")
                    or address.get("addressRegion")
                    or address.get("addressCountry")
                ) or "Not specified"
            elif isinstance(location_value, list):
                parts: list[str] = []
                for item in location_value:
                    if isinstance(item, dict):
                        address = item.get("address", {})
                        part = normalize_text(
                            address.get("addressLocality")
                            or address.get("addressRegion")
                            or address.get("addressCountry")
                        )
                        if part:
                            parts.append(part)
                location = ", ".join(parts) or "Not specified"

            jobs.append(
                {
                    "title": title,
                    "location": location,
                    "apply_link": normalize_url(node.get("url"), page_url),
                    "posted_at": normalize_text(node.get("datePosted")) or None,
                    "source": company.source,
                    "discovered_via": "json-ld",
                }
            )
    return jobs[:MAX_JOBS_PER_COMPANY]


def extract_generic_jobs(
    soup: BeautifulSoup,
    company: CompanyTarget,
    page_url: str,
) -> list[dict[str, str | None]]:
    jobs: list[dict[str, str | None]] = []
    seen: set[tuple[str, str]] = set()

    for anchor in soup.find_all("a", href=True):
        href = normalize_url(anchor.get("href"), page_url)
        if not href:
            continue

        anchor_text = normalize_title(anchor.get_text(" ", strip=True))
        container = anchor
        for _ in range(3):
            if container.parent is None:
                break
            container = container.parent
        context_text = normalize_text(container.get_text(" ", strip=True))

        candidate_title = anchor_text
        if not is_internship_title(candidate_title) and is_internship_title(context_text):
            heading = container.find(["h1", "h2", "h3", "h4"])
            candidate_title = normalize_title(
                heading.get_text(" ", strip=True) if heading else anchor_text or context_text
            )

        if not is_internship_title(candidate_title):
            continue

        key = (candidate_title.lower(), href.lower())
        if key in seen:
            continue
        seen.add(key)

        jobs.append(
            {
                "title": candidate_title,
                "location": guess_location(context_text),
                "apply_link": href,
                "posted_at": None,
                "source": company.source,
                "discovered_via": "generic-html",
            }
        )
        if len(jobs) >= MAX_JOBS_PER_COMPANY:
            break

    return jobs

