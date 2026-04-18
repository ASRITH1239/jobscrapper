from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
COMPANIES_PATH = BASE_DIR / "companies.json"
JOBS_PATH = BASE_DIR / "jobs.json"

INTERNSHIP_KEYWORDS = (
    "intern",
    "internship",
    "trainee",
    "apprentice",
    "co-op",
)

REQUEST_TIMEOUT_SECONDS = 30
PLAYWRIGHT_TIMEOUT_MS = 45_000
STALE_JOB_RETENTION_DAYS = 14
MAX_JOBS_PER_COMPANY = 30

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

DYNAMIC_DOMAIN_HINTS = (
    "workdayjobs",
    "myworkdayjobs",
    "greenhouse",
    "lever.co",
    "smartrecruiters",
    "ashbyhq",
    "recruitee",
    "jobvite",
    "successfactors",
)

LOCATION_PREFIXES = (
    "location",
    "locations",
    "based in",
    "remote",
    "hybrid",
    "onsite",
    "on-site",
)

