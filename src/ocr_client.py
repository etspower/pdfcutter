"""
Online OCR recognition using ocr.space API.

API docs: https://ocr.space/ocrapi
Endpoint: POST https://api.ocr.space/parse/image
Supports file upload, URL, and base64 image.
"""

import httpx
import base64
import json
import logging
from typing import List, Optional, Callable

logger = logging.getLogger(__name__)

OCR_SPACE_ENDPOINT = "https://api.ocr.space/parse/image"

# OCR Engine options:
# 1 = fastest, many languages, larger images
# 2 = better for special chars, rotated text, Latin + Chinese
# 3 = best accuracy, markdown tables, 200+ languages, slower
OCR_ENGINES = {
    "Engine 1 (Fast, Multi-lang)": 1,
    "Engine 2 (Special chars, Latin+CHS)": 2,
    "Engine 3 (Best accuracy, Markdown)": 3,
}

# Language codes supported by OCR.space Engine 1
OCR_LANGUAGES = {
    "English": "eng",
    "Chinese Simplified": "chs",
    "Chinese Traditional": "cht",
    "Japanese": "jpn",
    "Korean": "kor",
    "French": "fre",
    "German": "ger",
    "Spanish": "spa",
    "Russian": "rus",
    "Arabic": "ara",
    "Auto (Engine 2/3 only)": "auto",
}


def ocr_image_file(
    image_path: str,
    api_key: str,
    language: str = "eng",
    ocr_engine: int = 1,
    timeout: int = 60,
) -> dict:
    """
    Send a single image file to ocr.space and return the raw JSON response.

    Returns the full response dict from the API.
    """
    with open(image_path, "rb") as f:
        file_data = f.read()

    payload = {
        "apikey": api_key,
        "language": language,
        "isOverlayRequired": "false",
        "OCREngine": str(ocr_engine),
        "scale": "true",
        "isTable": "true",
    }

    files = {"file": (image_path.split("\\")[-1].split("/")[-1], file_data)}

    with httpx.Client(timeout=timeout) as client:
        response = client.post(OCR_SPACE_ENDPOINT, data=payload, files=files)
        response.raise_for_status()
        return response.json()


def extract_text_from_images_online(
    image_paths: List[str],
    api_key: str,
    language: str = "eng",
    ocr_engine: int = 1,
    timeout: int = 60,
    log_fn: Optional[Callable] = None,
) -> str:
    """
    OCR multiple images via ocr.space and return combined extracted text.

    Args:
        image_paths: List of local image file paths.
        api_key: ocr.space API key.
        language: OCR language code (e.g. 'eng', 'chs').
        ocr_engine: 1, 2, or 3.
        timeout: HTTP timeout in seconds.
        log_fn: Optional logging callback log_fn(msg, level).

    Returns:
        Combined text from all images.
    """
    def _log(msg, level="INFO"):
        if log_fn:
            log_fn(msg, level)
        else:
            logger.info(msg)

    all_texts = []

    for i, img_path in enumerate(image_paths):
        short_name = img_path.split("\\")[-1].split("/")[-1]
        _log(f"[Online OCR] Processing image {i+1}/{len(image_paths)}: {short_name}")

        try:
            result = ocr_image_file(img_path, api_key, language, ocr_engine, timeout)

            # Check for API-level errors
            if result.get("IsErroredOnProcessing", False):
                err_msg = result.get("ErrorMessage", ["Unknown error"])
                _log(f"[Online OCR] API error for {short_name}: {err_msg}", "ERROR")
                continue

            exit_code = result.get("OCRExitCode", 0)
            if exit_code not in (1, 2):
                _log(
                    f"[Online OCR] Unexpected exit code {exit_code} for {short_name}",
                    "WARN",
                )

            parsed_results = result.get("ParsedResults", [])
            for pr in parsed_results:
                file_exit = pr.get("FileParseExitCode", 0)
                if file_exit == 1:
                    text = pr.get("ParsedText", "")
                    if text.strip():
                        all_texts.append(text.strip())
                        _log(
                            f"[Online OCR] {short_name}: extracted {len(text)} chars",
                            "OK",
                        )
                else:
                    err = pr.get("ErrorMessage", "Unknown parse error")
                    _log(f"[Online OCR] Parse error for {short_name}: {err}", "ERROR")

            proc_time = result.get("ProcessingTimeInMilliseconds", "?")
            _log(f"[Online OCR] {short_name} processed in {proc_time}ms")

        except httpx.HTTPStatusError as e:
            _log(
                f"[Online OCR] HTTP error for {short_name}: {e.response.status_code} "
                f"{e.response.text[:300]}",
                "ERROR",
            )
        except Exception as e:
            _log(f"[Online OCR] Error processing {short_name}: {e}", "ERROR")

    combined = "\n\n".join(all_texts)
    _log(f"[Online OCR] Total extracted text: {len(combined)} chars from {len(all_texts)} page(s)", "OK")
    return combined


def test_ocr_space_connection(api_key: str, timeout: int = 15) -> bool:
    """
    Quick test of the ocr.space API key by sending a minimal request.
    Returns True if the API key is valid.
    """
    payload = {
        "apikey": api_key,
        "url": "https://dl.a9t9.com/ocr/solarcell.jpg",
        "language": "eng",
        "OCREngine": "1",
    }

    with httpx.Client(timeout=timeout) as client:
        response = client.post(OCR_SPACE_ENDPOINT, data=payload)
        response.raise_for_status()
        result = response.json()
        if result.get("IsErroredOnProcessing", False):
            raise Exception(f"API Error: {result.get('ErrorMessage', 'Unknown')}")
        return True
