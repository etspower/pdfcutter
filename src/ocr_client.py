import time
import asyncio
from typing import Callable, Optional
from llama_cloud import AsyncLlamaCloud


def extract_text_from_images_online(
    pdf_path: str,
    api_key: str,
    log_fn: Optional[Callable[[str, str], None]] = None,
) -> str:
    """
    Extract text using LlamaParse (LlamaIndex).
    We take the temp pdf_path and parse it.
    """
    if not log_fn:
        log_fn = lambda msg, level="INFO": print(f"[{level}] {msg}")

    if not api_key:
        raise ValueError("LlamaParse API Key is required for online extraction.")

    log_fn("Starting LlamaParse extraction...")
    
    # Run the async LlamaParse function in a synchronous wrapper
    try:
        result_text = asyncio.run(_run_llamaparse(pdf_path, api_key, log_fn))
        log_fn(f"LlamaParse: extracted {len(result_text)} chars", "OK")
        return result_text
    except Exception as e:
        log_fn(f"LlamaParse API Error: {e}", "ERROR")
        raise e


async def _run_llamaparse(pdf_path: str, api_key: str, log_fn: Callable) -> str:
    start_time = time.time()
    
    # Initialize the client
    client = AsyncLlamaCloud(api_key=api_key)
    
    log_fn("Uploading file to LlamaCloud...")
    file_obj = await client.files.create(file=pdf_path, purpose="parse")
    
    log_fn(f"File uploaded. ID: {file_obj.id}. Starting agentic parse...")
    result = await client.parsing.parse(
        file_id=file_obj.id,
        tier="agentic",
        expand=["markdown_full"],
    )
    
    end_time = time.time()
    log_fn(f"LlamaParse completed in {int(end_time - start_time)}s.")
    
    if result.markdown_full:
        return result.markdown_full
    elif result.text:
        return result.text
    else:
        return ""
