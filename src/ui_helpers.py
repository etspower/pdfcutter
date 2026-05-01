import pandas as pd
from typing import List, Dict
from src.schemas import TocEntry

def entries_to_dataframe(entries: List[TocEntry]) -> pd.DataFrame:
    data = []
    for e in entries:
        data.append({
            "enabled": e.enabled,
            "level": e.level,
            "title": e.title,
            "printed_page": str(e.printed_page) if e.printed_page is not None else "",
            "page_number_type": e.page_number_type,
            "pdf_start_page": e.pdf_start_page if e.pdf_start_page is not None else "",
            "pdf_end_page": e.pdf_end_page if e.pdf_end_page is not None else "",
            "output_name": e.output_name if e.output_name is not None else "",
            "warnings": "; ".join(e.warnings)
        })
    df = pd.DataFrame(data)
    if df.empty:
        df = pd.DataFrame(columns=["enabled", "level", "title", "printed_page", "page_number_type", "pdf_start_page", "pdf_end_page", "output_name", "warnings"])
    return df

def dataframe_to_entries(df: pd.DataFrame) -> List[TocEntry]:
    entries = []
    for _, row in df.iterrows():
        try:
            start_page = int(row["pdf_start_page"]) if str(row.get("pdf_start_page", "")).strip() else None
            end_page = int(row["pdf_end_page"]) if str(row.get("pdf_end_page", "")).strip() else None
            level = int(row.get("level", 1)) if str(row.get("level", "")).strip() else 1
            
            entries.append(TocEntry(
                enabled=bool(row.get("enabled", True)),
                level=level,
                title=str(row.get("title", "")),
                printed_page=str(row.get("printed_page", "")).strip() or None,
                page_number_type=row.get("page_number_type", "unknown"),
                pdf_start_page=start_page,
                pdf_end_page=end_page,
                output_name=str(row.get("output_name", "")),
                warnings=str(row.get("warnings", "")).split("; ") if str(row.get("warnings", "")) else []
            ))
        except Exception:
            pass
    return entries

def build_summary_markdown(entries: List[TocEntry]) -> str:
    total = len(entries)
    enabled = len([e for e in entries if e.enabled])
    warnings_count = sum(1 for e in entries if e.warnings)
    
    md = f"### TOC Summary\n"
    md += f"- **Total Entries:** {total}\n"
    md += f"- **Enabled Entries:** {enabled}\n"
    md += f"- **Entries with Warnings:** {warnings_count}\n\n"
    
    if warnings_count > 0:
        md += "#### Issues to review:\n"
        for i, e in enumerate(entries):
            if e.warnings:
                md += f"- **Row {i+1}** ({e.title}): {', '.join(e.warnings)}\n"
                
    return md
