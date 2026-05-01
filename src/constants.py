import os

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output"))
TEMP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "temp"))

DEFAULT_SYSTEM_PROMPT = """You are an expert at extracting tables of contents from book pages.
Look at the provided images of table of contents pages.
Extract each entry's title, printed page number, and logical heading level.
- level: integer. 1 for main chapters, 2 for sections, etc. Infer from indentation or typography.
- title: exact text of the heading. Do not include page numbers or decorative leader dots.
- printed_page: exactly as printed (e.g. "12", "xiv", "A1"). Can be null if missing.
- page_number_type: "arabic" for 1, 2, 3; "roman" for i, ii, iv; "unknown" for others or missing.
Return ONLY strict JSON matching the requested schema. Do NOT wrap in markdown codeblocks like ```json.
"""
