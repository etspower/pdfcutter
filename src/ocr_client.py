import time
import json
from typing import Callable, Optional
from llama_cloud import LlamaCloud


def extract_text_from_images_online(
    pdf_path: str,
    api_key: str,
    log_fn: Optional[Callable[[str, str], None]] = None,
) -> str:
    """
    Extract structured TOC data using LlamaParse (LlamaCloud Extract API).
    Returns a JSON string of the extracted entries.
    """
    if not log_fn:
        log_fn = lambda msg, level="INFO": print(f"[{level}] {msg}")

    if not api_key:
        raise ValueError("LlamaParse API Key is required for online extraction.")

    log_fn("Starting LlamaParse structured extraction...")
    
    start_time = time.time()
    try:
        # Initialize the synchronous client
        client = LlamaCloud(api_key=api_key)
        
        # Define schema for TOC extraction based on ModelTocResponse
        data_schema = {
            "type": "object",
            "properties": {
                "entries": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "level": {
                                "type": "integer", 
                                "description": "Hierarchical level of the entry (1 for main chapter, 2 for sub-chapter, etc.)"
                            },
                            "title": {
                                "type": "string", 
                                "description": "The exact title text of the chapter or section"
                            },
                            "printed_page": {
                                "type": "string", 
                                "description": "The page number as printed in the TOC (can be arabic 1, 2, 3... or roman i, ii, iii...)"
                            },
                            "page_number_type": {
                                "type": "string", 
                                "enum": ["arabic", "roman", "unknown"], 
                                "description": "The type of numbering used for the page"
                            }
                        },
                        "required": ["level", "title", "printed_page", "page_number_type"]
                    }
                }
            },
            "required": ["entries"]
        }

        log_fn("Uploading file to LlamaCloud...")
        file_obj = client.files.create(file=pdf_path, purpose="extract")
        
        log_fn(f"File uploaded. ID: {file_obj.id}. Starting agentic extraction...")
        
        # Use the Extract API to get structured data directly
        result = client.extract.run(
            file_input=file_obj.id,
            configuration={
                "data_schema": data_schema,
                "tier": "agentic",
                "extraction_target": "per_doc",
                "parse_tier": "agentic",
                "cite_sources": True,
                "confidence_scores": True
            },
        )
        
        end_time = time.time()
        duration = int(end_time - start_time)
        log_fn(f"LlamaParse completed in {duration}s.", "OK")
        
        if hasattr(result, 'extract_result') and result.extract_result:
            # result.extract_result is a dict following our schema
            return json.dumps(result.extract_result, ensure_ascii=False)
        else:
            log_fn("LlamaParse returned no extract_result", "WARN")
            return "{}"

    except Exception as e:
        log_fn(f"LlamaParse API Error: {e}", "ERROR")
        raise e
