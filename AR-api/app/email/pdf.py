"""PDF attachment helper for payment confirmation emails."""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

ASSETS_DIR = Path(__file__).parent / "assets"
BASE_AGREEMENT_PDF = ASSETS_DIR / "service_agreement.pdf"
SIGNATURE_FONT_TTF = ASSETS_DIR / "signature_font.ttf"

SIGNATURE_FONT_NAME = "SignatureFont"

SIGNATURE_X = 72
SIGNATURE_Y = 415
SIGNATURE_FONT_SIZE = 24
SIGNATURE_PAGE_INDEX = -1

TIMESTAMP_Y_OFFSET = 20
TIMESTAMP_FONT_SIZE = 10

SIGNATURE_TIMEZONE = "UTC"


def _format_timestamp_with_timezone(iso_timestamp: str) -> str:
    """
    Format an ISO timestamp to include timezone and full datetime.

    Input can be ISO format with or without timezone info.
    Output format: 2026-03-12T13:38:50 UTC

    Args:
        iso_timestamp: ISO format timestamp string.

    Returns:
        Formatted timestamp with timezone.
    """
    from datetime import datetime, timezone

    if not iso_timestamp:
        return ""

    try:
        if iso_timestamp.endswith("Z"):
            iso_timestamp = iso_timestamp[:-1] + "+00:00"

        dt = datetime.fromisoformat(iso_timestamp)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)

        return f"{dt.strftime('%Y-%m-%dT%H:%M:%S')} {SIGNATURE_TIMEZONE}"
    except (ValueError, TypeError):
        logger.warning("Failed to parse timestamp: %s", iso_timestamp)
        return iso_timestamp


@dataclass
class SignatureData:
    """Data for the signature overlay on the agreement PDF."""

    signature: str
    signed_at: str
    customer_email: str
    channels: list[str]


def load_agreement_pdf() -> bytes | None:
    """
    Return the raw bytes of the base agreement PDF, or None if the file has
    not been placed in ``app/email/assets/service_agreement.pdf``.
    """
    if not BASE_AGREEMENT_PDF.exists():
        logger.debug(
            "No base agreement PDF found at %s; skipping attachment.", BASE_AGREEMENT_PDF
        )
        return None

    return BASE_AGREEMENT_PDF.read_bytes()


def _register_signature_font() -> str:
    """
    Register the signature font if the TTF file exists.

    Returns the font name to use (custom font or fallback).
    """
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    if SIGNATURE_FONT_TTF.exists():
        try:
            pdfmetrics.registerFont(TTFont(SIGNATURE_FONT_NAME, str(SIGNATURE_FONT_TTF)))
            logger.debug("Registered signature font from %s", SIGNATURE_FONT_TTF)
            return SIGNATURE_FONT_NAME
        except Exception:
            logger.warning(
                "Failed to register signature font from %s; using fallback",
                SIGNATURE_FONT_TTF,
                exc_info=True,
            )
    else:
        logger.debug(
            "No signature font found at %s; using fallback", SIGNATURE_FONT_TTF
        )

    return "Helvetica-Oblique"


def _create_signature_overlay(
    signature: str, signed_at: str | None, page_width: float, page_height: float
) -> bytes:
    """
    Create a transparent PDF overlay with the signature and timestamp.

    The signature is positioned at SIGNATURE_X, SIGNATURE_Y from the bottom-left.
    The timestamp is placed below the signature.

    Returns the PDF as bytes.
    """
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(page_width, page_height))

    signature_font = _register_signature_font()

    if signature:
        c.setFont(signature_font, SIGNATURE_FONT_SIZE)
        c.drawString(SIGNATURE_X, SIGNATURE_Y, signature)

        if signed_at:
            c.setFont("Helvetica", TIMESTAMP_FONT_SIZE)
            timestamp_y = SIGNATURE_Y - TIMESTAMP_Y_OFFSET
            formatted_timestamp = _format_timestamp_with_timezone(signed_at)
            c.drawString(SIGNATURE_X, timestamp_y, f"Signed: {formatted_timestamp}")

    c.save()
    buffer.seek(0)
    return buffer.read()


def create_signed_agreement_pdf(data: SignatureData) -> bytes | None:
    """
    Load the base agreement PDF and overlay the signature on the LICENSEE section.

    The signature is placed on the last page at the configured position.

    Returns the combined PDF as bytes, or None if the base PDF does not exist.
    """
    from pypdf import PdfReader, PdfWriter

    base_pdf_bytes = load_agreement_pdf()
    if base_pdf_bytes is None:
        return None

    base_reader = PdfReader(io.BytesIO(base_pdf_bytes))
    writer = PdfWriter()

    sig_page_index = SIGNATURE_PAGE_INDEX
    if sig_page_index < 0:
        sig_page_index = len(base_reader.pages) + sig_page_index

    for i, page in enumerate(base_reader.pages):
        if i == sig_page_index and data.signature:
            page_width = float(page.mediabox.width)
            page_height = float(page.mediabox.height)

            overlay_bytes = _create_signature_overlay(
                data.signature, data.signed_at, page_width, page_height
            )
            overlay_reader = PdfReader(io.BytesIO(overlay_bytes))
            overlay_page = overlay_reader.pages[0]

            page.merge_page(overlay_page)

        writer.add_page(page)

    output = io.BytesIO()
    writer.write(output)
    output.seek(0)

    logger.debug(
        "Created signed agreement PDF with signature on page %d", sig_page_index + 1
    )
    return output.read()
