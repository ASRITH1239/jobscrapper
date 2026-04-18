from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True)
class CompanyTarget:
    company: str
    career_page_url: str
    category: str
    type: str
    dynamic: bool = False
    source: str = "career-page"

    @classmethod
    def from_dict(cls, payload: dict) -> "CompanyTarget":
        return cls(
            company=payload["company"].strip(),
            career_page_url=payload["career_page_url"].strip(),
            category=payload.get("category", "General").strip(),
            type=payload.get("type", "Unknown").strip(),
            dynamic=bool(payload.get("dynamic", False)),
            source=payload.get("source", "career-page").strip(),
        )


@dataclass(slots=True)
class JobRecord:
    id: str
    title: str
    company: str
    location: str
    apply_link: str
    category: str
    type: str
    source: str
    scraped_at: str
    first_seen_at: str
    last_seen_at: str
    posted_at: str | None = None
    discovered_via: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class ScrapeFailure:
    company: str
    url: str
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class ScrapeResult:
    jobs: list[JobRecord] = field(default_factory=list)
    failures: list[ScrapeFailure] = field(default_factory=list)

