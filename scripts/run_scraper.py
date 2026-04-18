from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from internship_aggregator.pipeline import load_companies, run_pipeline  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape internship listings into jobs.json.")
    parser.add_argument("--companies", default=str(ROOT / "companies.json"))
    parser.add_argument("--jobs", default=str(ROOT / "jobs.json"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--skip-dynamic",
        action="store_true",
        help="Skip Playwright and only use requests/BeautifulSoup.",
    )
    args = parser.parse_args()

    companies_path = Path(args.companies)
    jobs_path = Path(args.jobs)

    companies = load_companies(companies_path)
    payload = run_pipeline(
        companies,
        existing_jobs_path=jobs_path,
        skip_dynamic=args.skip_dynamic,
        limit=args.limit,
    )
    jobs_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    print(
        f"Stored {payload['stats']['total_jobs']} jobs "
        f"from {payload['stats']['scraped_companies']} companies into {jobs_path}"
    )


if __name__ == "__main__":
    main()
