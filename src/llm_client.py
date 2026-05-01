import httpx
import base64
from typing import List, Optional
import json

def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def test_connection(base_url: str, api_key: str, model: str, timeout: int) -> bool:
    headers = {"Authorization": f"Bearer {api_key}"}
    if not api_key:
        headers = {} # for local models without auth
        
    try:
        with httpx.Client(timeout=timeout) as client:
            # Try getting models as a simple test, or just sending a tiny chat request
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": "hello"}],
                "max_tokens": 5
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
    system_prompt: str
) -> str:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if not api_key:
        headers = {"Content-Type": "application/json"}
        
    content = []
    for img_path in image_paths:
        base64_image = encode_image(img_path)
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            }
        })
    content.append({
        "type": "text",
        "text": "Please extract the table of contents from these images. Return JSON matching the schema."
    })

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
                        "page_number_type": {"type": "string", "enum": ["arabic", "roman", "unknown"]}
                    },
                    "required": ["level", "title", "page_number_type"]
                }
            }
        },
        "required": ["entries"]
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "toc_extraction",
                "schema": schema,
                "strict": True
            }
        }
    }
    
    # Fallback to normal json object if schema isn't supported
    fallback_payload = dict(payload)
    fallback_payload["response_format"] = {"type": "json_object"}

    url = f"{base_url.rstrip('/')}/chat/completions"
    
    with httpx.Client(timeout=timeout) as client:
        try:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code in [400, 422]: # Maybe strict schema not supported
                response = client.post(url, headers=headers, json=fallback_payload)
                response.raise_for_status()
            else:
                raise
                
    result = response.json()
    return result["choices"][0]["message"]["content"]
