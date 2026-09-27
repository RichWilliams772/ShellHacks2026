# Aaron Green
# Extracts page text from the two source PDFs the pipeline already cites, so the
# dashboard assistant can quote them. One chunk per page, page number kept as
# provenance. Run once; the backend reads the JSON this writes, it never opens
# a PDF itself.

import json
import re
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "data" / "processed" / "assistant_document_chunks.json"

# Same citation strings already used for these two PDFs in
# teco_projects_geocoded.csv's project_source / circuit_endpoint_source columns.
DOCUMENTS = [
    {
        "pdf": ROOT / "data" / "TECO.pdf",
        "document_id": "teco_storm_protection_plan",
        "document_title": (
            "Tampa Electric Modified 2026-2035 Storm Protection Plan, "
            "FPSC Docket No. 20250016-EI, Exhibit KEP-1"
        ),
    },
    {
        "pdf": ROOT / "data" / "EI806-24-AR(GEO).pdf",
        "document_id": "teco_fpsc_annual_report_2024",
        "document_title": "Tampa Electric Company FPSC Annual Report 2024 (FERC Form 1 schedules)",
    },
]

# Below this, a page is near-blank or a scanned image with no text layer -
# not worth indexing and not a tuned relevance threshold.
MIN_CHARS = 40


def squash(text):
    return re.sub(r"[ \t]+", " ", text).strip()


def build_chunks():
    chunks = []
    for doc in DOCUMENTS:
        with pdfplumber.open(doc["pdf"]) as pdf:
            for i, page in enumerate(pdf.pages):
                text = squash(page.extract_text() or "")
                if len(text) < MIN_CHARS:
                    continue
                chunks.append(
                    {
                        "chunk_id": f"{doc['document_id']}_p{i + 1}",
                        "document_id": doc["document_id"],
                        "document_title": doc["document_title"],
                        "page": i + 1,
                        "text": text,
                    }
                )
    return chunks


def main():
    chunks = build_chunks()
    OUT_JSON.write_text(json.dumps(chunks, indent=2), encoding="utf-8")
    print(f"wrote {len(chunks)} chunks to {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
