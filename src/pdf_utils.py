from pypdf import PdfReader, PdfWriter
import fitz  # PyMuPDF
import os
from typing import List, Tuple
import zipfile
from src.constants import TEMP_DIR, OUTPUT_DIR

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_pdf_info(pdf_path: str) -> int:
    reader = PdfReader(pdf_path)
    return len(reader.pages)


def parse_page_range(range_str: str, max_pages: int) -> List[int]:
    pages = set()
    parts = range_str.split(',')
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                if start > end:
                    start, end = end, start
                start = max(1, start)
                end = min(max_pages, end)
                pages.update(range(start, end + 1))
            except ValueError:
                pass
        else:
            try:
                page = int(part)
                if 1 <= page <= max_pages:
                    pages.add(page)
            except ValueError:
                pass
    return sorted(list(pages))


def extract_toc_images(pdf_path: str, pages: List[int]) -> List[str]:
    """Render PDF pages to JPEG using PyMuPDF (no Poppler required)."""
    image_paths = []
    doc = fitz.open(pdf_path)
    try:
        for page_num in pages:  # 1-indexed
            page_idx = page_num - 1
            if page_idx < 0 or page_idx >= len(doc):
                continue
            page = doc[page_idx]
            # 2x zoom for higher resolution / better OCR quality
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            img_path = os.path.join(TEMP_DIR, f"toc_page_{page_num}.jpg")
            pix.save(img_path)
            image_paths.append(img_path)
    finally:
        doc.close()
    return image_paths


def split_pdf(pdf_path: str, plan: List[dict], output_prefix: str) -> Tuple[List[str], str]:
    reader = PdfReader(pdf_path)
    output_files = []

    for item in plan:
        if not item['enabled']:
            continue

        start_idx = item['start_page'] - 1  # 0-indexed
        end_idx = item['end_page']          # exclusive

        writer = PdfWriter()
        for i in range(start_idx, min(end_idx, len(reader.pages))):
            writer.add_page(reader.pages[i])

        safe_name = item['output_name']
        out_filename = f"{output_prefix}_{safe_name}.pdf"
        out_path = os.path.join(OUTPUT_DIR, out_filename)

        with open(out_path, "wb") as f:
            writer.write(f)
        output_files.append(out_path)

    zip_filename = f"{output_prefix}_splits.zip"
    zip_path = os.path.join(OUTPUT_DIR, zip_filename)
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for f in output_files:
            zipf.write(f, os.path.basename(f))

    return output_files, zip_path
