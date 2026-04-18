from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from internship_aggregator.utils import normalize_text, source_label_for_url, should_use_dynamic_fetch

WORD_NAMESPACE = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
CATEGORY_RE = re.compile(r"^(?P<name>.+?)\s+\((?P<count>\d+)\)$")


def extract_paragraphs(docx_path: Path) -> list[str]:
    with zipfile.ZipFile(docx_path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))

    paragraphs: list[str] = []
    for para in root.findall(".//w:p", WORD_NAMESPACE):
        text = "".join(node.text or "" for node in para.findall(".//w:t", WORD_NAMESPACE)).strip()
        if text:
            paragraphs.append(normalize_text(text))
    return paragraphs


def parse_companies(paragraphs: list[str]) -> list[dict]:
    companies: list[dict] = []
    i = 0
    while i < len(paragraphs):
        category_match = CATEGORY_RE.match(paragraphs[i])
        if not category_match:
            i += 1
            continue

        i += 1
        while i < len(paragraphs) and paragraphs[i] in {"#", "Company Name", "Career Page URL", "Category", "Type"}:
            i += 1

        while i + 4 < len(paragraphs) and paragraphs[i].isdigit():
            row_number = int(paragraphs[i])
            company_name = paragraphs[i + 1]
            career_page_url = paragraphs[i + 2]
            category = paragraphs[i + 3]
            company_type = paragraphs[i + 4]

            if not career_page_url.startswith("http"):
                break

            companies.append(
                {
                    "row_number": row_number,
                    "company": company_name,
                    "career_page_url": career_page_url,
                    "category": category,
                    "type": company_type,
                    "dynamic": should_use_dynamic_fetch(career_page_url),
                    "source": source_label_for_url(career_page_url),
                }
            )
            i += 5
        continue
    return companies


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert the DOCX company list into companies.json.")
    parser.add_argument(
        "--docx",
        default=r"C:\Users\acer\Downloads\internship_companies_500plus.docx",
        help="Path to the source DOCX file.",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "companies.json"),
        help="Path to write the parsed JSON company list.",
    )
    args = parser.parse_args()

    docx_path = Path(args.docx)
    output_path = Path(args.output)

    paragraphs = extract_paragraphs(docx_path)
    companies = parse_companies(paragraphs)
    output_path.write_text(json.dumps(companies, indent=2, ensure_ascii=True), encoding="utf-8")
    print(f"Wrote {len(companies)} companies to {output_path}")


if __name__ == "__main__":
    main()
