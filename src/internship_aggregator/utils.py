from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from html import unescape
from typing import Any
from urllib.parse import urljoin, urlparse

from internship_aggregator.config import INTERNSHIP_KEYWORDS, LOCATION_PREFIXES

WHITESPACE_RE = re.compile(r"\s+")
JSON_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")
LOCATION_SPLIT_RE = re.compile(r"[|•\n]+")


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    candidate = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(candidate)
    except ValueError:
        return None


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return WHITESPACE_RE.sub(" ", unescape(value)).strip()


def normalize_title(value: str | None) -> str:
    return normalize_text(value).replace("–", "-")


def normalize_url(raw_url: str | None, base_url: str | None = None) -> str:
    if not raw_url:
        return ""
    url = normalize_text(raw_url)
    if base_url:
        url = urljoin(base_url, url)
    return url


def source_label_for_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "linkedin.com" in host:
        return "linkedin"
    if "indeed." in host:
        return "indeed"
    if "internshala.com" in host:
        return "internshala"
    return "career-page"


def should_use_dynamic_fetch(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(hint in host for hint in (
        "workdayjobs",
        "myworkdayjobs",
        "greenhouse",
        "lever.co",
        "smartrecruiters",
        "ashbyhq",
        "recruitee",
        "jobvite",
        "successfactors",
    ))


def is_internship_title(title: str) -> bool:
    candidate = normalize_title(title).lower()
    return any(keyword in candidate for keyword in INTERNSHIP_KEYWORDS)


def dedupe_hash(title: str, company: str, apply_link: str) -> str:
    digest = hashlib.sha256()
    digest.update(normalize_title(title).lower().encode("utf-8"))
    digest.update(b"::")
    digest.update(normalize_text(company).lower().encode("utf-8"))
    digest.update(b"::")
    digest.update(normalize_url(apply_link).lower().encode("utf-8"))
    return digest.hexdigest()


def guess_location(text: str) -> str:
    content = normalize_text(text)
    if not content:
        return "Not specified"

    lower = content.lower()
    for prefix in LOCATION_PREFIXES:
        if prefix in lower:
            start = lower.index(prefix)
            snippet = content[start:start + 120]
            parts = LOCATION_SPLIT_RE.split(snippet)
            if parts:
                cleaned = normalize_text(parts[0].split(":", 1)[-1])
                if cleaned:
                    return cleaned.title() if cleaned.islower() else cleaned

    city_match = re.search(
        r"\b(Remote|Hybrid|Bengaluru|Bangalore|Mumbai|Pune|Hyderabad|Chennai|Noida|"
        r"Gurugram|Gurgaon|Delhi|Kolkata|Ahmedabad|India)\b",
        content,
        re.IGNORECASE,
    )
    if city_match:
        return city_match.group(1)
    return "Not specified"


def safe_json_loads(raw_text: str) -> Any:
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        repaired = JSON_TRAILING_COMMA_RE.sub(r"\1", raw_text.strip())
        return json.loads(repaired)


def is_new_within_24h(iso_timestamp: str | None, now: datetime | None = None) -> bool:
    parsed = parse_datetime(iso_timestamp)
    if not parsed:
        return False
    now = now or utc_now()
    return parsed >= now - timedelta(hours=24)

