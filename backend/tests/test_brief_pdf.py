"""Coordination Brief PDFs copy a stored opportunity and do not rescore it."""

from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient
from pypdf import PdfReader

from app.config import Settings
from app.main import create_app

TOP_ID = "DUKE-P0132__TECO-138005"
client = TestClient(create_app(settings=Settings(project_catalog="processed")))


def _text(payload: bytes) -> str:
    reader = PdfReader(BytesIO(payload))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def test_known_pair_brief_is_a_pdf() -> None:
    response = client.get(f"/opportunities/{TOP_ID}/brief.pdf")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    disposition = response.headers["content-disposition"]
    assert disposition.startswith("attachment;")
    assert f'filename="GridSync-{TOP_ID}.pdf"' in disposition
    assert response.content.startswith(b"%PDF-")
    text = _text(response.content)
    assert "GridSync" in text
    assert "See the overlap. Build the grid together." in text
    assert TOP_ID in text
    assert "Disston to Largo Transmission Upgrade" in text
    assert "Transmission Upgrades-138/230 kV-138005" in text
    assert "Duke Energy Florida" in text
    assert "Tampa Electric" in text
    assert "Coordination score: 63.3/100" in text
    assert "not a probability of coordination" in text
    assert "15.05 miles is the minimum distance between known project endpoints." in text
    assert "An exact schedule overlap is not confirmed." in text
    assert "Known project endpoints are approximately 15.0 miles apart" in text
    assert (
        "Text comparison of project names and types shares terms related to transmission, upgrade."
        in text
    )
    assert "Both projects are categorized as Transmission upgrade." in text
    assert "transmission_upgrade" not in text
    assert "Project descriptions share terms" not in text
    assert "Source URL: missing from this record." in text
    assert "has no source_url" in text
    assert "https://www.duke-energy.com/" in text
    assert "Data: public" in text
    assert "0 months" not in text


def test_unknown_pair_brief_is_not_found() -> None:
    response = client.get("/opportunities/DUKE-NOPE__TECO-NOPE/brief.pdf")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
