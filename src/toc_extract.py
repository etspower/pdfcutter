import json
from src.schemas import TocExtractionResult, TocEntry, ModelTocResponse
from pydantic import ValidationError

def clean_json_string(raw_text: str) -> str:
    raw_text = raw_text.strip()
    if raw_text.startswith("```json"):
        raw_text = raw_text[7:]
    if raw_text.startswith("```"):
        raw_text = raw_text[3:]
    if raw_text.endswith("```"):
        raw_text = raw_text[:-3]
    return raw_text.strip()

def parse_extraction_result(raw_text: str, toc_pages: list[int], model_name: str) -> TocExtractionResult:
    cleaned = clean_json_string(raw_text)
    notes = []
    entries = []
    
    try:
        data = json.loads(cleaned)
        # Try to validate with pydantic
        model_resp = ModelTocResponse(**data)
        
        for item in model_resp.entries:
            entries.append(TocEntry(
                level=item.level,
                title=item.title,
                printed_page=item.printed_page,
                page_number_type=item.page_number_type
            ))
            
    except json.JSONDecodeError as e:
        notes.append(f"JSON Parse Error: {str(e)}")
    except ValidationError as e:
        notes.append(f"Schema Validation Error: {str(e)}")
    except Exception as e:
        notes.append(f"Unexpected Error: {str(e)}")
        
    return TocExtractionResult(
        toc_pages=toc_pages,
        entries=entries,
        notes=notes,
        raw_response_text=raw_text,
        model_name=model_name
    )
