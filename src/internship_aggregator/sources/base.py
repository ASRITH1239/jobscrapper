from __future__ import annotations

from abc import ABC, abstractmethod

from internship_aggregator.models import CompanyTarget, ScrapeResult


class BaseSourceScraper(ABC):
    @abstractmethod
    def matches(self, company: CompanyTarget) -> bool:
        raise NotImplementedError

    @abstractmethod
    def scrape(self, company: CompanyTarget) -> ScrapeResult:
        raise NotImplementedError

