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
            
    except (json.JSONDecodeError, ValidationError) as e:
        # Fallback to regex parsing if raw_text is plain OCR text
        import re
        lines = raw_text.splitlines()
        for line in lines:
            line = line.strip()
            if not line: continue
            
            title = ""
            page_str = ""

            if line.startswith("|") and line.endswith("|"):
                # Docling Markdown table format
                cells = [c.strip() for c in line.strip("|").split("|")]
                if len(cells) >= 2:
                    possible_page = cells[-1]
                    if re.match(r"^([IVXLCDMivxlcdm\d]+)$", possible_page):
                        page_str = possible_page
                        # Join all non-empty columns except the last one as title
                        text_cells = [c for c in cells[:-1] if c and len(c) > 1 and not re.match(r"^[\-\|]+$", c)]
                        title = " ".join(text_cells)
            else:
                # Online OCR / Plain text format
                # Match Title ending with a number, separated by spaces or dots
                match = re.search(r"^(.*?)(?:\s{2,}|\.{2,}|\_{2,}|\-{2,}|\s+)([IVXLCDMivxlcdm\d]+)$", line)
                if match:
                    title = match.group(1).strip()
                    page_str = match.group(2).strip()

            if title and page_str:
                # Remove leading/trailing artifacts
                title = re.sub(r"^[.\-_|]+|[.\-_|]+$", "", title).strip()
                # Validate title: must contain letters/characters and not be too long
                if len(title) > 2 and len(title) < 80 and re.search(r"[a-zA-Z\u4e00-\u9fa5]", title):
                    page_type = "arabic" if page_str.isdigit() else "roman"
                    entries.append(TocEntry(
                        level=1,
                        title=title,
                        printed_page=page_str,
                        page_number_type=page_type
                    ))
        
        if entries:
            notes.append(f"Parsed {len(entries)} entries using regex fallback.")
        else:
            notes.append(f"JSON Parse Error: {str(e)} and Regex fallback yielded 0 entries.")
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
