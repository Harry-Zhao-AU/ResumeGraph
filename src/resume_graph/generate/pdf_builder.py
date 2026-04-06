"""Step 2b: Render resume markdown to PDF with varied visual styles using reportlab."""

from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    HRFlowable,
)

RESUMES_DIR = Path("data/resumes")


# --- Style Definitions ---

def _base_styles():
    return getSampleStyleSheet()


def style_clean() -> dict[str, ParagraphStyle]:
    """Minimal, lots of whitespace."""
    return {
        "name": ParagraphStyle(
            "name", fontName="Helvetica-Bold", fontSize=18, spaceAfter=2 * mm,
            alignment=TA_CENTER,
        ),
        "contact": ParagraphStyle(
            "contact", fontName="Helvetica", fontSize=9, spaceAfter=4 * mm,
            alignment=TA_CENTER, textColor=HexColor("#666666"),
        ),
        "heading": ParagraphStyle(
            "heading", fontName="Helvetica-Bold", fontSize=12, spaceBefore=6 * mm,
            spaceAfter=2 * mm, textColor=HexColor("#2C3E50"),
        ),
        "body": ParagraphStyle(
            "body", fontName="Helvetica", fontSize=10, leading=14,
            spaceAfter=2 * mm,
        ),
        "bullet": ParagraphStyle(
            "bullet", fontName="Helvetica", fontSize=10, leading=14,
            leftIndent=10 * mm, bulletIndent=5 * mm, spaceAfter=1 * mm,
        ),
        "hr_color": HexColor("#CCCCCC"),
        "margin": 2.5 * cm,
    }


def style_compact() -> dict[str, ParagraphStyle]:
    """Dense, professional."""
    return {
        "name": ParagraphStyle(
            "name", fontName="Helvetica-Bold", fontSize=16, spaceAfter=1 * mm,
        ),
        "contact": ParagraphStyle(
            "contact", fontName="Helvetica", fontSize=8, spaceAfter=3 * mm,
            textColor=HexColor("#555555"),
        ),
        "heading": ParagraphStyle(
            "heading", fontName="Helvetica-Bold", fontSize=11, spaceBefore=4 * mm,
            spaceAfter=1.5 * mm, textColor=HexColor("#1A1A1A"),
        ),
        "body": ParagraphStyle(
            "body", fontName="Helvetica", fontSize=9, leading=12,
            spaceAfter=1.5 * mm,
        ),
        "bullet": ParagraphStyle(
            "bullet", fontName="Helvetica", fontSize=9, leading=12,
            leftIndent=8 * mm, bulletIndent=3 * mm, spaceAfter=0.5 * mm,
        ),
        "hr_color": HexColor("#999999"),
        "margin": 1.8 * cm,
    }


def style_modern() -> dict[str, ParagraphStyle]:
    """Colored headers, contemporary feel."""
    return {
        "name": ParagraphStyle(
            "name", fontName="Helvetica-Bold", fontSize=20, spaceAfter=2 * mm,
            textColor=HexColor("#1E88E5"),
        ),
        "contact": ParagraphStyle(
            "contact", fontName="Helvetica", fontSize=9, spaceAfter=4 * mm,
            textColor=HexColor("#757575"),
        ),
        "heading": ParagraphStyle(
            "heading", fontName="Helvetica-Bold", fontSize=12, spaceBefore=5 * mm,
            spaceAfter=2 * mm, textColor=HexColor("#1E88E5"),
        ),
        "body": ParagraphStyle(
            "body", fontName="Helvetica", fontSize=10, leading=14,
            spaceAfter=2 * mm,
        ),
        "bullet": ParagraphStyle(
            "bullet", fontName="Helvetica", fontSize=10, leading=14,
            leftIndent=10 * mm, bulletIndent=5 * mm, spaceAfter=1 * mm,
        ),
        "hr_color": HexColor("#1E88E5"),
        "margin": 2.2 * cm,
    }


def style_traditional() -> dict[str, ParagraphStyle]:
    """Times New Roman, conservative."""
    return {
        "name": ParagraphStyle(
            "name", fontName="Times-Bold", fontSize=16, spaceAfter=2 * mm,
            alignment=TA_CENTER,
        ),
        "contact": ParagraphStyle(
            "contact", fontName="Times-Roman", fontSize=10, spaceAfter=4 * mm,
            alignment=TA_CENTER, textColor=HexColor("#333333"),
        ),
        "heading": ParagraphStyle(
            "heading", fontName="Times-Bold", fontSize=12, spaceBefore=5 * mm,
            spaceAfter=2 * mm,
        ),
        "body": ParagraphStyle(
            "body", fontName="Times-Roman", fontSize=10, leading=14,
            spaceAfter=2 * mm,
        ),
        "bullet": ParagraphStyle(
            "bullet", fontName="Times-Roman", fontSize=10, leading=14,
            leftIndent=10 * mm, bulletIndent=5 * mm, spaceAfter=1 * mm,
        ),
        "hr_color": HexColor("#000000"),
        "margin": 2.5 * cm,
    }


STYLES = [style_clean, style_compact, style_modern, style_traditional]


def _escape(text: str) -> str:
    """Escape XML special chars for reportlab Paragraph."""
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    return text


def _parse_markdown_to_flowables(markdown: str, styles: dict) -> list:
    """Convert resume markdown to reportlab flowables."""
    flowables = []
    lines = markdown.strip().split("\n")
    i = 0
    is_first_heading = True

    while i < len(lines):
        line = lines[i].strip()

        # Skip empty lines
        if not line:
            i += 1
            continue

        # H1 — name
        if line.startswith("# ") and not line.startswith("## "):
            text = _escape(line[2:].strip())
            flowables.append(Paragraph(text, styles["name"]))
            is_first_heading = True
            i += 1
            continue

        # H2 — section heading
        if line.startswith("## "):
            text = _escape(line[3:].strip())
            if not is_first_heading:
                flowables.append(
                    HRFlowable(
                        width="100%", thickness=0.5,
                        color=styles.get("hr_color", HexColor("#CCCCCC")),
                        spaceAfter=2 * mm,
                    )
                )
            is_first_heading = False
            flowables.append(Paragraph(text, styles["heading"]))
            i += 1
            continue

        # H3 — sub-heading (job title, etc.)
        if line.startswith("### "):
            text = _escape(line[4:].strip())
            flowables.append(
                Paragraph(f"<b>{text}</b>", styles["body"])
            )
            i += 1
            continue

        # Bullet point
        if line.startswith("- ") or line.startswith("* "):
            text = _escape(line[2:].strip())
            # Handle bold markers
            text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
            flowables.append(
                Paragraph(f"\u2022 {text}", styles["bullet"])
            )
            i += 1
            continue

        # Contact line (email, location — usually right after name)
        if "@" in line and i < 5:
            text = _escape(line.strip("*_ "))
            flowables.append(Paragraph(text, styles["contact"]))
            i += 1
            continue

        # Regular paragraph
        text = _escape(line)
        text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
        flowables.append(Paragraph(text, styles["body"]))
        i += 1

    return flowables


def render_pdf(markdown: str, output_path: Path, style_index: int = 0) -> None:
    """Render resume markdown to PDF with a specific visual style."""
    style_fn = STYLES[style_index % len(STYLES)]
    styles = style_fn()
    margin = styles.pop("margin", 2.5 * cm)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
    )

    flowables = _parse_markdown_to_flowables(markdown, styles)
    if flowables:
        doc.build(flowables)


def render_all(resumes: list[tuple[str, str]]) -> None:
    """Render all resumes to PDFs with varied styles."""
    RESUMES_DIR.mkdir(parents=True, exist_ok=True)

    for i, (stem, markdown) in enumerate(resumes):
        output_path = RESUMES_DIR / f"{stem}.pdf"
        render_pdf(markdown, output_path, style_index=i)
        print(f"  PDF: {output_path.name} (style: {STYLES[i % len(STYLES)].__name__})")
