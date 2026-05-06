# pdfcutter

[English](README.md) | [简体中文](README_zh.md) | [Français (Canada)](README_fr_CA.md)

A local desktop application for splitting scanned language learning PDFs based on their Table of Contents (TOC). 

`pdfcutter` uses advanced OCR (Online/Offline) and vision-capable Large Language Models (LLMs) to read the TOC from PDF pages, automatically extract chapter headings and page numbers, and then slices the original PDF into individual chapter files.

## Features
- **Flexible Recognition Modes:**
  - **Online OCR (ocr.space):** Fast, supports 20+ languages and multiple OCR engines.
  - **Offline OCR (Docling):** Local, high-accuracy document conversion with layout analysis. No API key required.
- **AI-Powered Extraction:** Uses vision models (via OpenRouter/NVIDIA) or text-based structured extraction from OCR results.
- **Review & Edit:** See the extracted TOC in a structured table. Edit errors, add/remove entries, and recalculate PDF page mappings.
- **Split & Download:** Generate individual PDF files for each chapter and download them as a ZIP archive.
- **Native Desktop GUI:** Built with Flet for a smooth desktop experience.

## Prerequisites

- **Python 3.10+**
- **Poppler:** Required for `pymupdf` and `pdf2image` image extraction (if using image-based workflows).
- **OCR.space API Key (Optional):** If you want to use the online recognition mode. Get a free key at [ocr.space](https://ocr.space/ocrapi).

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
    Edit `.env` to include your `OCR_SPACE_API_KEY` or LLM credentials.

## Running the App

Run the desktop application:
```bash
python gui.py
```

## How it Works

1. **Step 1: Config & Upload:** Select your PDF and specify the TOC page range. Choose between **Online (ocr.space)** or **Offline (Docling)** recognition.
2. **Step 2: Preview & Run:** Preview the TOC pages and click **Run OCR Extraction**. The app extracts text from images and optionally uses an LLM to structure it into JSON.
3. **Step 3: Review & Edit:** The app computes an offset based on the first identified Arabic page number. You can manually adjust titles, levels, or PDF start pages here.
4. **Step 4: Execute Split:** Review the split plan and click **Split PDF & Save**.

## Architecture
- **GUI (`gui.py`)**: Flet-based desktop interface.
- **OCR Clients (`src/ocr_client.py`, `src/docling_client.py`)**: Integration with ocr.space (online) and Docling (offline).
- **LLM Client (`src/llm_client.py`)**: Structured data extraction using vision or text-based LLM prompts.
- **PDF Utils (`src/pdf_utils.py`)**: PDF rendering and splitting using `PyMuPDF` and `pypdf`.
- **Logic Modules (`src/toc_extract.py`, `src/split_logic.py`)**: Data validation and page offset calculations.

## License
MIT
