"""Render one stored opportunity as a Coordination Brief PDF.

The brief copies fields already on the opportunity. It does not rescore the pair.
"""

from __future__ import annotations

import re
from io import BytesIO
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.models import Opportunity, Project

_NA = "Not available"
_NAVY = HexColor("#0b1220")
_INK = HexColor("#1b2230")
_MUTED = HexColor("#5b6472")
_TAGLINE = "See the overlap. Build the grid together."
_DESCRIPTION_TERMS = "Project descriptions share terms"
_NAME_TYPE_TERMS = "Text comparison of project names and types shares terms"
# Field names in evidence gaps stay literal. They are not project types.
_NOT_PROJECT_TYPES = frozenset({"source_url", "source_name"})
_SNAKE_CASE = re.compile(r"\b[a-z]+(?:_[a-z0-9]+)+\b")


def render_coordination_brief(opportunity: Opportunity) -> bytes:
    """Return PDF bytes for this retrieved opportunity."""
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title=f"GridSync {opportunity.id}",
        author="GridSync",
    )
    styles = _styles()
    story: list[Paragraph | Spacer] = [
        Paragraph("GridSync", styles["title"]),
        Paragraph(_safe(_TAGLINE), styles["tagline"]),
        Spacer(1, 8),
        Paragraph(_safe(_data_line(opportunity)), styles["meta"]),
        Spacer(1, 12),
        *_section("Pair", _pair_lines(opportunity), styles),
        *_section("Coordination score", _score_lines(opportunity), styles),
        *_section("Distance", [_distance_line(opportunity)], styles),
        *_section("Timing", _timing_lines(opportunity), styles),
        *_section("Why this pair matched", _match_lines(opportunity.reasons), styles),
        *_section("Potential shared resources", _resource_lines(opportunity), styles),
        *_section("Evidence gaps", _bullets(opportunity.evidence_gaps), styles),
        *_section(opportunity.project_a.utility, _project_lines(opportunity.project_a), styles),
        *_section(opportunity.project_b.utility, _project_lines(opportunity.project_b), styles),
    ]
    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


def _styles() -> dict[str, ParagraphStyle]:
    return {
        "title": ParagraphStyle(
            "BriefTitle",
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=_NAVY,
            spaceAfter=2,
        ),
        "tagline": ParagraphStyle(
            "BriefTagline",
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            textColor=_MUTED,
        ),
        "meta": ParagraphStyle(
            "BriefMeta",
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=_MUTED,
        ),
        "heading": ParagraphStyle(
            "BriefHeading",
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=_NAVY,
            spaceBefore=10,
            spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "BriefBody",
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=_INK,
            spaceAfter=2,
        ),
    }


def _section(
    heading: str,
    lines: list[str],
    styles: dict[str, ParagraphStyle],
) -> list[Paragraph | Spacer]:
    blocks: list[Paragraph | Spacer] = [Paragraph(_safe(heading), styles["heading"])]
    for line in lines:
        blocks.append(Paragraph(_safe(line), styles["body"]))
    return blocks


def _footer(canvas: Any, doc: Any) -> None:
    canvas.saveState()
    canvas.setFillColor(_MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(0.75 * inch, 0.4 * inch, "GridSync coordination brief")
    canvas.drawRightString(letter[0] - 0.75 * inch, 0.4 * inch, f"Page {doc.page}")
    canvas.restoreState()


def _data_line(opportunity: Opportunity) -> str:
    if opportunity.data_type == "demo" or _project_is_demo(opportunity):
        return "Data: demo"
    if opportunity.data_type == "mixed":
        return "Data: mixed. This brief includes demo data."
    return "Data: public"


def _project_is_demo(opportunity: Opportunity) -> bool:
    return opportunity.project_a.data_type == "demo" or opportunity.project_b.data_type == "demo"


def _pair_lines(opportunity: Opportunity) -> list[str]:
    left = opportunity.project_a
    right = opportunity.project_b
    return [
        f"Pair ID: {opportunity.id}",
        f"{left.project_name} ({left.utility})",
        f"{right.project_name} ({right.utility})",
    ]


def _score_lines(opportunity: Opportunity) -> list[str]:
    score = opportunity.coordination_score
    if score is None:
        score_text = f"Coordination score: {_NA}"
    else:
        score_text = f"Coordination score: {_number(score)}/100"
    interpretation = opportunity.score_interpretation.strip() or _NA
    return [score_text, interpretation]


def _distance_line(opportunity: Opportunity) -> str:
    miles = opportunity.features.distance_miles
    if miles is None:
        return f"Distance: {_NA}"
    label = (opportunity.features.distance_label or "").casefold()
    amount = _number(miles)
    if "endpoint" in label:
        return f"{amount} miles is the minimum distance between known project endpoints."
    if opportunity.features.distance_label:
        return f"{amount} miles. {opportunity.features.distance_label}."
    return f"{amount} miles."


def _timing_lines(opportunity: Opportunity) -> list[str]:
    features = opportunity.features
    lines: list[str] = []
    precision = features.temporal_precision
    if precision is None:
        lines.append(f"Timing precision: {_NA}")
    else:
        lines.append(f"Timing precision: {precision}")
    if features.schedule_overlap_months is None:
        if precision == "mixed":
            lines.append(
                "An exact schedule overlap is not confirmed. "
                "The available schedules use mixed date precision."
            )
        else:
            lines.append(f"Exact schedule overlap: {_NA}")
    else:
        lines.append(
            f"Recorded schedule overlap: {_number(features.schedule_overlap_months)} months."
        )
    if features.year_difference is None:
        lines.append(f"Year difference: {_NA}")
    else:
        lines.append(f"Recorded year difference: {_number(features.year_difference)}.")
    if features.same_active_year is True:
        lines.append(
            "The records show activity in the same calendar year. "
            "That is not a confirmed exact schedule overlap."
        )
    elif features.same_active_year is False:
        lines.append("Same active year: no.")
    return lines


def _resource_lines(opportunity: Opportunity) -> list[str]:
    package = opportunity.coordination_package
    rows = package.resources or package.shared_resources
    if not rows:
        note = package.evidence_note.strip()
        return [note or "None recorded."]
    lines = [f"{row.label}: {row.strength}" for row in rows]
    if package.evidence_note.strip():
        lines.append(package.evidence_note.strip())
    return lines


def _project_lines(project: Project) -> list[str]:
    lines = [
        project.project_name,
        f"Project ID: {project.id}",
        f"Source name: {project.source_name.strip() or _NA}",
    ]
    if project.source_url and project.source_url.strip():
        lines.append(f"Source URL: {project.source_url.strip()}")
    else:
        lines.append("Source URL: missing from this record.")
    if project.data_type == "demo":
        lines.append("Project data: demo.")
    return lines


def _match_lines(reasons: list[str]) -> list[str]:
    """Display copy for stored reasons. The opportunity record is not rewritten."""
    return _bullets([_display_reason(reason) for reason in reasons])


def _display_reason(reason: str) -> str:
    text = reason.replace(_DESCRIPTION_TERMS, _NAME_TYPE_TERMS)
    return _humanize_types(text)


def _humanize_types(text: str) -> str:
    """`transmission_upgrade` -> `Transmission upgrade`. Stored values stay unchanged."""

    def replace(match: re.Match[str]) -> str:
        token = match.group(0)
        if token in _NOT_PROJECT_TYPES:
            return token
        words = token.replace("_", " ")
        return words[0].upper() + words[1:]

    return _SNAKE_CASE.sub(replace, text)


def _bullets(items: list[str]) -> list[str]:
    cleaned = [item.strip() for item in items if item.strip()]
    if not cleaned:
        return ["None recorded."]
    return [f"- {item}" for item in cleaned]


def _number(value: float) -> str:
    text = f"{value:.10f}".rstrip("0").rstrip(".")
    return text or "0"


def _safe(text: str) -> str:
    """Keep ReportLab's standard font from rejecting characters outside Latin-1."""
    cleaned = text.encode("latin-1", errors="replace").decode("latin-1")
    return escape(cleaned)
