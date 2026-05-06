# pdfcutter

[English](README.md) | [简体中文](README_zh.md) | [Français (Canada)](README_fr_CA.md)

A local desktop application for splitting scanned language learning PDFs based on their Table of Contents (TOC). 

`pdfcutter` uses advanced OCR (Online/Offline) to read the TOC from PDF pages, automatically extract chapter headings and page numbers, and then slices the original PDF into individual chapter files.

## Features
- **Flexible Recognition Modes:**
  - **Online OCR (LlamaParse):** Agentic document parsing using LlamaIndex's LlamaCloud, highly accurate for complex tables and lists.
  - **Offline OCR (Docling):** Local, high-accuracy document conversion with layout analysis. No API key required.
- **Automated Extraction:** Extracts text from OCR results and parses it into a structured table format.
- **Review & Edit:** See the extracted TOC in a structured table. Edit errors, add/remove entries, and recalculate PDF page mappings.
- **Page Offset Control:** Easily adjust the mapping between printed page numbers and actual PDF page numbers using a global offset (with +/- buttons).
- **Live Page Preview:** Preview any page in the PDF instantly within the mapping table to verify accuracy before splitting.
- **Split & Download:** Generate individual PDF files for each chapter and download them as a ZIP archive.
- **Native Desktop GUI:** Built with Flet for a smooth desktop experience.

## Prerequisites

- **Python 3.10+**
- **Poppler:** Required for `pymupdf` and `pdf2image` image extraction.
- **LlamaParse API Key (Optional):** If you want to use the online recognition mode. Get a free key at [LlamaCloud](https://cloud.llamaindex.ai).

## Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/etspower/pdfcutter.git
    cd pdfcutter
    ```

2. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
    *Note: Installing `docling` for offline OCR will download approximately 500MB of models on first run.*

3. Setup environment variables:
    ```bash
    cp .env.example .env
    ```
    Edit `.env` to include your `LLAMAPARSE_API_KEY`.

## Running the App

Run the desktop application:
```bash
python gui.py
```

## How it Works

1. **Step 1: Config & Upload:** Select your PDF and specify the TOC page range. Choose between **Online (LlamaParse)** or **Offline (Docling)** recognition.
2. **Step 2: Preview & Run:** Preview the TOC pages and click **Run OCR Extraction**. The app extracts text and structures it into a editable list.
3. **Step 3: Review & Edit:** The app computes an initial offset based on the TOC. You can manually adjust this **Global Offset** using +/- buttons to align all pages, and use the **Preview button** (eye icon) on each row to verify the PDF page mapping in real-time.
4. **Step 4: Execute Split:** Review the split plan and click **Split PDF & Save**.

## Architecture
- **GUI (`gui.py`)**: Flet-based desktop interface.
- **OCR Clients (`src/ocr_client.py`, `src/docling_client.py`)**: Integration with LlamaParse (online) and Docling (offline).
- **PDF Utils (`src/pdf_utils.py`)**: PDF rendering and splitting using `PyMuPDF` and `pypdf`.
- **Logic Modules (`src/toc_extract.py`, `src/split_logic.py`)**: Data validation and page offset calculations.

## Credits & Special Thanks
This project is built upon the following amazing open-source projects:
- [Docling](https://docling-project.github.io/docling/) - For powerful local OCR and document conversion.
- [LlamaParse](https://github.com/run-llama/llama_parse) - For state-of-the-art online document parsing capabilities.
- [Flet](https://flet.dev/) - For enabling the creation of beautiful desktop apps with Python.
- [PyMuPDF](https://pymupdf.readthedocs.io/) & [pypdf](https://pypdf.readthedocs.io/) - For PDF manipulation and rendering.

## License
MIT
