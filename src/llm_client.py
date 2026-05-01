import httpx
import base64
import io
from typing import List
from PIL import Image

# NVIDIA NIM recommended limit: ~180 KB per image after base64
_MAX_IMAGE_BYTES = 180_000  # bytes (base64-decoded)
_JPEG_QUALITY_START = 85


def _encode_image(image_path: str) -> str:
    """Open image, downscale + compress until base64 payload <= _MAX_IMAGE_BYTES."""
    img = Image.open(image_path).convert("RGB")

    quality = _JPEG_QUALITY_START
    scale = 1.0

    for _ in range(10):  # max 10 attempts
        buf = io.BytesIO()
        w = int(img.width * scale)
        h = int(img.height * scale)
        resized = img.resize((w, h), Image.LANCZOS) if scale < 1.0 else img
        resized.save(buf, format="JPEG", quality=quality, optimize=True)
        raw = buf.getvalue()
        if len(raw) <= _MAX_IMAGE_BYTES:
            break
        # reduce quality first, then scale
        if quality > 40:
            quality -= 15
        else:
            scale *= 0.75

    return base64.b64encode(raw).decode("utf-8")


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
) -> str:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if not api_key:
        headers = {"Content-Type": "application/json"}

    # Build vision content, compressing each image
    content = []
    for img_path in image_paths:
        b64 = _encode_image(img_path)
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
            }
        )
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

    # Try strict json_schema first, fall back to json_object on any error
    strict_payload = {
        "model": model,
        "messages": base_messages,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "toc_extraction",
                "schema": schema,
                "strict": True,
            },
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
            resp = client.post(url, headers=headers, json=strict_payload)
            resp.raise_for_status()
        except httpx.HTTPStatusError:
            # Any HTTP error (400, 422, 500 …) → retry without strict schema
            resp = client.post(url, headers=headers, json=fallback_payload)
            resp.raise_for_status()

    return resp.json()["choices"][0]["message"]["content"]
