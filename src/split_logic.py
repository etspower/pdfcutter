import re
from typing import List
from src.schemas import TocEntry, SplitPlanItem

def roman_to_int(s: str) -> int:
    roman_values = {'i': 1, 'v': 5, 'x': 10, 'l': 50, 'c': 100, 'd': 500, 'm': 1000}
    s = str(s).lower()
    total = 0
    prev_value = 0
    for char in reversed(s):
        if char not in roman_values:
            return 0
        value = roman_values[char]
        if value < prev_value:
            total -= value
        else:
            total += value
        prev_value = value
    return total

def sanitize_filename(name: str) -> str:
    name = re.sub(r'[^\w\s-]', '', name).strip()
    name = re.sub(r'[-\s]+', '_', name)
    return name[:50]

def compute_page_mapping(entries: List[TocEntry], total_pdf_pages: int, last_toc_pdf_page: int) -> List[TocEntry]:
    # Find the first arabic page to determine offset
    offset = None
    
    for i, entry in enumerate(entries):
        if not entry.enabled:
            continue
        if entry.page_number_type == "arabic" and entry.printed_page is not None:
            try:
                printed_num = int(entry.printed_page)
                # Heuristic: offset = actual_pdf_page - printed_page
                # We assume the first arabic page starts immediately after the last TOC page
                if offset is None:
                    estimated_pdf_page = last_toc_pdf_page + 1
                    offset = estimated_pdf_page - printed_num
                    entry.warnings.append(f"Estimated offset: {offset}")
            except ValueError:
                pass

    if offset is None:
        offset = 0
        if entries:
            entries[0].warnings.append("Could not determine offset, using 0.")

    # Assign pdf_start_page
    for entry in entries:
        entry.warnings = [] # clear previous warnings
        if not entry.enabled:
            entry.pdf_start_page = None
            continue
            
        if entry.printed_page is None:
            entry.warnings.append("Missing printed page.")
            continue
            
        if entry.page_number_type == "arabic":
            try:
                entry.pdf_start_page = int(entry.printed_page) + offset
            except ValueError:
                entry.warnings.append(f"Invalid arabic page: {entry.printed_page}")
        elif entry.page_number_type == "roman":
            val = roman_to_int(str(entry.printed_page))
            if val > 0:
                # Typically front matter has 0 offset or a different offset. 
                # Let's just use the value directly + some front cover offset if needed, 
                # but for simplicity assume roman = pdf page if covers are included, or needs manual adjustment
                entry.pdf_start_page = val
                entry.warnings.append("Roman numeral mapping might be inaccurate.")
            else:
                entry.warnings.append(f"Invalid roman numeral: {entry.printed_page}")
        else:
            entry.warnings.append("Unknown page number type.")

    # Calculate end pages
    enabled_entries = [e for e in entries if e.enabled and e.pdf_start_page is not None]
    
    for i in range(len(enabled_entries)):
        current = enabled_entries[i]
        
        if i + 1 < len(enabled_entries):
            next_entry = enabled_entries[i + 1]
            current.pdf_end_page = next_entry.pdf_start_page - 1
            if current.pdf_end_page < current.pdf_start_page:
                current.warnings.append("End page < Start page (overlapping or decreasing).")
        else:
            current.pdf_end_page = total_pdf_pages
            
        current.output_name = f"{current.pdf_start_page:03d}_{sanitize_filename(current.title)}"

    return entries

def generate_split_plan(entries: List[TocEntry]) -> List[SplitPlanItem]:
    plan = []
    for entry in entries:
        if entry.enabled and entry.pdf_start_page is not None and entry.pdf_end_page is not None:
            plan.append(SplitPlanItem(
                enabled=entry.enabled,
                title=entry.title,
                start_page=entry.pdf_start_page,
                end_page=entry.pdf_end_page,
                output_name=entry.output_name or sanitize_filename(entry.title),
                warnings=entry.warnings
            ))
    return plan
