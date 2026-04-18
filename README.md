# Internship Radar

Internship Radar is a fully serverless internship aggregator built with Python scraping, a static HTML/CSS/JS frontend, and GitHub Actions automation. It is designed to stay free to run:

- Python scraper uses `requests` + BeautifulSoup for static pages.
- Playwright is used only when a site needs JavaScript rendering.
- Results are normalized into `jobs.json`.
- GitHub Actions refreshes the feed every 6 hours and commits changes back to the repository.
- GitHub Pages can host the frontend for free.

## Repository layout

- `companies.json`: input list of company targets.
- `jobs.json`: normalized internship feed used by the frontend.
- `scripts/generate_companies_json.py`: converts the provided DOCX list into `companies.json`.
- `scripts/run_scraper.py`: scraper entrypoint used locally and in CI.
- `src/internship_aggregator/`: reusable scraper package.
- `site/`: static frontend deployed to GitHub Pages.
- `.github/workflows/scrape.yml`: scheduled scraping workflow.
- `.github/workflows/deploy-pages.yml`: static site deployment workflow.

## Job schema

Each job entry inside `jobs.json` uses a consistent schema:

```json
{
  "id": "sha256(title+company+apply_link)",
  "title": "Software Engineer Intern",
  "company": "Example Co",
  "location": "Bengaluru",
  "apply_link": "https://example.com/jobs/123",
  "category": "Tech MNC",
  "type": "Paid",
  "source": "career-page",
  "posted_at": null,
  "scraped_at": "2026-04-19T12:00:00+00:00",
  "first_seen_at": "2026-04-19T12:00:00+00:00",
  "last_seen_at": "2026-04-19T12:00:00+00:00",
  "discovered_via": "json-ld"
}
```

## Local setup

1. Create a virtual environment and install dependencies.
2. Generate `companies.json` from the DOCX list if needed.
3. Run the scraper.
4. Serve the static frontend locally.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/generate_companies_json.py
python scripts/run_scraper.py --limit 25
python -m http.server 8080
```

Then open `http://localhost:8080/site/`.

## How scraping works

- Internship filtering is keyword-based: `intern`, `internship`, `trainee`, `apprentice`, and `co-op`.
- JSON-LD `JobPosting` data is parsed first because many career sites expose structured job metadata.
- If JSON-LD is missing, the scraper falls back to HTML anchor and container parsing.
- LinkedIn, Indeed, and Internshala have dedicated basic selectors when their URLs are included in `companies.json`.
- Deduplication uses a SHA-256 hash of `title`, `company`, and `apply_link`.
- Existing jobs keep their original `first_seen_at` so the frontend can highlight listings that are new in the last 24 hours.
- Jobs not seen in the latest scrape are retained for 14 days to reduce churn from flaky career sites.

## GitHub Actions

### Scheduled scraper

The scraper workflow runs every 6 hours and on manual dispatch:

```yaml
schedule:
  - cron: "0 */6 * * *"
```

It installs Chromium for Playwright, runs the scraper, and commits `jobs.json` if the feed changed.

### GitHub Pages deployment

The Pages workflow deploys `site/` plus the latest `jobs.json` whenever `main` changes. To use it:

1. Push this repository to GitHub.
2. In repository settings, enable GitHub Pages with GitHub Actions as the source.
3. Make sure your default branch is `main`.

## Extending the scraper

To add new source types later:

1. Create a new scraper in `src/internship_aggregator/sources/`.
2. Implement `matches()` and `scrape()`.
3. Register it in `run_pipeline()` before the generic career page scraper.

## Notes

- LinkedIn, Indeed, and some ATS platforms may rate-limit or change markup frequently, so those integrations are best-effort rather than guaranteed.
- GitHub Actions scheduled workflows can be paused by GitHub after long periods of repository inactivity.
- This project stays fully free as long as you use GitHub Actions and a static host like GitHub Pages.
