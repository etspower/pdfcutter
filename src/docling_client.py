"""
Offline OCR recognition using Docling (https://docling-project.github.io/docling/).

Docling provides local, offline document conversion with advanced layout analysis,
table recognition, and text extraction. No API key needed.
"""

import logging
from typing import List, Optional, Callable

logger = logging.getLogger(__name__)


def extract_text_from_pdf_offline(
    pdf_path: str,
    pages: Optional[List[int]] = None,
    log_fn: Optional[Callable] = None,
) -> str:
    """
    Use Docling to extract text from a PDF file locally (offline).

    Args:
        pdf_path: Path to the PDF file.
        pages: Optional list of 1-indexed page numbers to extract.
                If None, extracts from all pages.
        log_fn: Optional logging callback log_fn(msg, level).

    Returns:
        Extracted text in markdown format.
    """
    def _log(msg, level="INFO"):
        if log_fn:
            log_fn(msg, level)
        else:
            logger.info(msg)

    try:
        from docling.document_converter import DocumentConverter
    except ImportError:
        _log(
            "[Offline OCR] docling is not installed. "
            "Please install it with: pip install docling",
            "ERROR",
        )
        raise ImportError(
            "docling is not installed. Install with: pip install docling"
        )

    _log(f"[Offline OCR] Starting Docling conversion for: {pdf_path}")
    _log("[Offline OCR] This may take a while on first run (downloading models)...")

    try:
        converter = DocumentConverter()
        result = converter.convert(pdf_path)
        doc = result.document

        _log("[Offline OCR] Conversion complete. Exporting to markdown...", "OK")

        # Export to markdown — this preserves structure, tables, headings
        full_text = doc.export_to_markdown()

        if pages:
            _log(
                f"[Offline OCR] Note: Docling processes the full PDF. "
                f"Page filtering ({pages}) is applied at TOC extraction level.",
                "INFO",
            )

        _log(
            f"[Offline OCR] Extracted {len(full_text)} chars of markdown text.",
            "OK",
        )
        return full_text

    except Exception as e:
        _log(f"[Offline OCR] Docling conversion error: {e}", "ERROR")
        raise


def extract_text_from_images_offline(
    image_paths: List[str],
    log_fn: Optional[Callable] = None,
) -> str:
    """
    Use Docling to extract text from image files locally (offline).

    Args:
        image_paths: List of image file paths.
        log_fn: Optional logging callback log_fn(msg, level).

    Returns:
        Combined extracted text in markdown format.
    """
    def _log(msg, level="INFO"):
        if log_fn:
            log_fn(msg, level)
        else:
            logger.info(msg)

    try:
        from docling.document_converter import DocumentConverter
    except ImportError:
        _log(
            "[Offline OCR] docling is not installed. "
            "Please install it with: pip install docling",
            "ERROR",
        )
        raise ImportError(
            "docling is not installed. Install with: pip install docling"
        )

    _log(f"[Offline OCR] Processing {len(image_paths)} image(s) with Docling...")
    _log("[Offline OCR] This may take a while on first run (downloading models)...")

    converter = DocumentConverter()
    all_texts = []

    for i, img_path in enumerate(image_paths):
        short_name = img_path.split("\\")[-1].split("/")[-1]
        _log(f"[Offline OCR] Converting image {i+1}/{len(image_paths)}: {short_name}")

        try:
            result = converter.convert(img_path)
            doc = result.document
            text = doc.export_to_markdown()

            if text.strip():
                all_texts.append(text.strip())
                _log(
                    f"[Offline OCR] {short_name}: extracted {len(text)} chars",
                    "OK",
                )
            else:
                _log(f"[Offline OCR] {short_name}: no text extracted", "WARN")

        except Exception as e:
            _log(f"[Offline OCR] Error processing {short_name}: {e}", "ERROR")

    combined = "\n\n".join(all_texts)
    _log(
        f"[Offline OCR] Total: {len(combined)} chars from {len(all_texts)} image(s)",
        "OK",
    )
    return combined


def check_docling_available() -> bool:
    """Check if docling is installed and importable."""
    try:
        from docling.document_converter import DocumentConverter
        return True
    except ImportError:
        return False
