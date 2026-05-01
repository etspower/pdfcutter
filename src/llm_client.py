import httpx
import base64
import io
import logging
from typing import List
from PIL import Image

logger = logging.getLogger(__name__)

# NVIDIA NIM recommended limit: ~180 KB per image (raw bytes before base64)
_MAX_IMAGE_BYTES = 180_000
_JPEG_QUALITY_START = 85

# Known vision-capable models on NVIDIA NIM (as of 2025)
NVIDIA_VISION_MODELS = [
    "microsoft/phi-3.5-vision-instruct",
    "nvidia/llama-3.2-11b-vision-instruct",
    "nvidia/llama-3.2-90b-vision-instruct",
    "google/gemma-3-27b-it",
    "meta/llama-4-scout-17b-16e-instruct",
    "meta/llama-4-maverick-17b-128e-instruct",
]


def _encode_image(image_path: str) -> tuple[str, int, int]:
    """
    Compress image to <= _MAX_IMAGE_BYTES, return (base64_str, original_kb, final_kb).
    """
    img = Image.open(image_path).convert("RGB")
    original_size = img.width * img.height * 3  # rough estimate

    quality = _JPEG_QUALITY_START
    scale = 1.0
    raw = b""

    for _ in range(12):
        buf = io.BytesIO()
        w = max(1, int(img.width * scale))
        h = max(1, int(img.height * scale))
        resized = img.resize((w, h), Image.LANCZOS) if scale < 1.0 else img
        resized.save(buf, format="JPEG", quality=quality, optimize=True)
        raw = buf.getvalue()
        if len(raw) <= _MAX_IMAGE_BYTES:
            break
        if quality > 40:
            quality -= 15
        else:
            scale *= 0.7

    final_kb = len(raw) // 1024
    orig_kb = original_size // 1024
    return base64.b64encode(raw).decode("utf-8"), orig_kb, final_kb


def test_connection(base_url: str, api_key: str, model: str, timeout: int) -> bool:
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        with httpx.Client(timeout=timeout) as client:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": "hello"}],
                "max_tokens": 5,
            }
            url = f"{base_url.rstrip('/')}/chat/completions"
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return True
    except Exception as e:
        raise Exception(f"Connection failed: {str(e)}")


def extract_toc_from_images(
    image_paths: List[str],
    base_url: str,
    api_key: str,
    model: str,
    timeout: int,
    system_prompt: str,
    log_fn=None,  # optional callback: log_fn(msg, level)
) -> str:
    def _log(msg, level="INFO"):
        if log_fn:
            log_fn(msg, level)
        else:
            logger.info(msg)

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if not api_key:
        headers = {"Content-Type": "application/json"}

    # Check if model looks like a vision model
    model_lower = model.lower()
    looks_like_vision = any(
        kw in model_lower for kw in ["vision", "vl", "llava", "phi-3.5", "llama-4", "gemma-3"]
    )
    if not looks_like_vision:
        _log(
            f"WARNING: model '{model}' may not support vision/image input. "
            f"Recommended vision models: {', '.join(NVIDIA_VISION_MODELS)}",
            "WARN",
        )

    # Compress and encode images
    content = []
    total_kb = 0
    for img_path in image_paths:
        b64, orig_kb, final_kb = _encode_image(img_path)
        total_kb += final_kb
        _log(f"Image compressed: {img_path.split('/')[-1].split(chr(92))[-1]}  "
             f"~{orig_kb} KB raw → {final_kb} KB sent")
        content.append(
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
        )
    _log(f"Total image payload: ~{total_kb} KB")

    content.append(
        {
            "type": "text",
            "text": (
                "Please extract the table of contents from these images. "
                "Return JSON matching the schema."
            ),
        }
    )

    schema = {
        "type": "object",
        "properties": {
            "entries": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "level": {"type": "integer"},
                        "title": {"type": "string"},
                        "printed_page": {"type": ["string", "integer", "null"]},
                        "page_number_type": {
                            "type": "string",
                            "enum": ["arabic", "roman", "unknown"],
                        },
                    },
                    "required": ["level", "title", "page_number_type"],
                },
            }
        },
        "required": ["entries"],
    }

    base_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content},
    ]

    strict_payload = {
        "model": model,
        "messages": base_messages,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "toc_extraction", "schema": schema, "strict": True},
        },
    }
    fallback_payload = {
        "model": model,
        "messages": base_messages,
        "response_format": {"type": "json_object"},
    }

    url = f"{base_url.rstrip('/')}/chat/completions"

    with httpx.Client(timeout=timeout) as client:
        try:
            _log("Sending request (strict json_schema)…")
            resp = client.post(url, headers=headers, json=strict_payload)
            if not resp.is_success:
                _log(f"API error body: {resp.text[:500]}", "WARN")
            resp.raise_for_status()
        except httpx.HTTPStatusError as first_err:
            _log(
                f"Strict schema failed ({first_err.response.status_code}), "
                "retrying with json_object fallback…",
                "WARN",
            )
            resp = client.post(url, headers=headers, json=fallback_payload)
            if not resp.is_success:
                err_body = resp.text[:800]
                _log(f"Fallback also failed. API error body:\n{err_body}", "ERROR")
                # Give user actionable hint for 500 on vision
                if resp.status_code == 500:
                    _log(
                        "HTTP 500 often means the model does not support image input. "
                        f"Try one of: {', '.join(NVIDIA_VISION_MODELS)}",
                        "ERROR",
                    )
            resp.raise_for_status()

    return resp.json()["choices"][0]["message"]["content"]
