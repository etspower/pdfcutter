# pdfcutter

A local Gradio web app for splitting scanned language learning PDFs based on their Table of Contents (TOC). 

`pdfcutter` uses vision-capable Large Language Models (LLMs) to read the TOC from the images of the PDF pages, automatically extract the chapter headings and their corresponding page numbers, and then slices the original PDF into multiple individual chapter files.

## Features
- **Upload & Config:** Upload a PDF and specify the page range where the TOC is located. Configure OpenAI-compatible API details.
- **TOC Preview:** View the extracted TOC pages as images.
- **Review & Edit:** See the AI-extracted TOC in a structured table. Edit any errors, add or remove entries, and let the app recalculate the actual PDF page mappings.
- **Split & Download:** Generate individual PDF files for each chapter and download them all as a single ZIP archive.

## Prerequisites

This app uses `pdf2image` to convert PDF pages into images. It requires `poppler` to be installed on your system.

### Installing Poppler (Linux / GitHub Codespaces)

```bash
sudo apt-get update
sudo apt-get install -y poppler-utils
```

## Installation

1. Clone the repository and navigate to the directory:
    ```bash
    git clone https://github.com/yourusername/pdfcutter.git
    cd pdfcutter
    ```

2. Create a virtual environment and install the requirements:
    ```bash
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3. Create a `.env` file from the example:
    ```bash
    cp .env.example .env
    ```
    Then, edit the `.env` file with your API credentials and preferences.

## Running the App

```bash
python app.py
```
The app will be available at `http://localhost:7860`.

## Architecture
- **Gradio App (`app.py`)**: The main user interface with tabs for each step of the process.
- **PDF Utils (`src/pdf_utils.py`)**: Handlers for counting pages, converting pages to images using `pdf2image`, and splitting the PDF with `pypdf`.
- **LLM Client (`src/llm_client.py`)**: A generic OpenAI-compatible API client using `httpx` to send image inputs to the vision model and enforce JSON output.
- **Extraction & Splitting Logic (`src/toc_extract.py`, `src/split_logic.py`)**: Parses the raw JSON response, validates it via Pydantic schemas, and computes offset mappings to translate printed page numbers into actual PDF indices.

## Known Limitations
- The offset calculation is heuristic based on the first Arabic page number found. If the front matter structure is complex, you may need to manually edit the starting PDF pages in the "Review & Edit" tab.
- Very large PDFs might take some time to split or render.

## Manual Test Workflow
1. Start the app.
2. Upload a sample PDF.
3. Check the "TOC Page Ranges" and enter `1-2` (or wherever your TOC is).
4. Click "Extract TOC Images" and look at the "TOC Preview" tab.
5. In "Upload & Config", ensure your `.env` values are loaded or manually enter your API Key and Model Name (e.g., `gpt-4o`).
6. Go to "TOC Preview" and click "Run AI TOC Extraction".
7. Check the results in "Review & Edit". Fix any misidentified page numbers.
8. Go to "Split & Download" and click "Split PDF & Create ZIP".
9. Download the ZIP and verify the slices.
