import gradio as gr
import os
import pandas as pd
from dotenv import load_dotenv

from src.config import Config
from src.pdf_utils import get_pdf_info, parse_page_range, extract_toc_images, split_pdf
from src.llm_client import test_connection, extract_toc_from_images
from src.toc_extract import parse_extraction_result
from src.split_logic import compute_page_mapping, generate_split_plan
from src.ui_helpers import entries_to_dataframe, dataframe_to_entries, build_summary_markdown
from src.schemas import TocEntry

# Load defaults
load_dotenv()

def load_env_defaults():
    load_dotenv(override=True)
    return (
        os.getenv("PDFCUTTER_API_BASE_URL", "https://api.openai.com/v1"),
        os.getenv("PDFCUTTER_API_KEY", ""),
        os.getenv("PDFCUTTER_MODEL", "gpt-4o"),
        int(os.getenv("PDFCUTTER_TIMEOUT", "60")),
        os.getenv("PDFCUTTER_SYSTEM_PROMPT", Config.SYSTEM_PROMPT)
    )

def handle_test_conn(base_url, api_key, model, timeout):
    try:
        success = test_connection(base_url, api_key, model, timeout)
        if success:
            return "✅ Connection successful!"
    except Exception as e:
        return f"❌ Connection failed: {str(e)}"

def process_pdf_upload(pdf_file):
    if not pdf_file:
        return 0, ""
    pages = get_pdf_info(pdf_file.name)
    return pages, f"Loaded PDF with {pages} pages."

def extract_images(pdf_file, toc_range_str, total_pages):
    if not pdf_file or not toc_range_str:
        return [], [], "Please upload a PDF and specify TOC pages."
    
    pages_to_extract = parse_page_range(toc_range_str, total_pages)
    if not pages_to_extract:
        return [], [], "Invalid page range."
        
    image_paths = extract_toc_images(pdf_file.name, pages_to_extract)
    return image_paths, image_paths, f"Extracted {len(image_paths)} images."

def run_extraction(image_paths, base_url, api_key, model, timeout, sys_prompt, total_pdf_pages):
    if not image_paths:
        return "No images to extract", pd.DataFrame(), "Please extract images first."
        
    try:
        raw_text = extract_toc_from_images(image_paths, base_url, api_key, model, timeout, sys_prompt)
        
        # We need a dummy toc_pages list for now
        toc_pages = [i for i in range(len(image_paths))]
        
        result = parse_extraction_result(raw_text, toc_pages, model)
        
        # Apply initial mapping logic
        last_toc_page = 1 # Dummy fallback
        mapped_entries = compute_page_mapping(result.entries, total_pdf_pages, last_toc_page)
        
        df = entries_to_dataframe(mapped_entries)
        summary = build_summary_markdown(mapped_entries)
        
        return raw_text, df, summary
    except Exception as e:
        return f"Error: {str(e)}", pd.DataFrame(), "Extraction failed."

def recompute_mapping(df, total_pdf_pages):
    entries = dataframe_to_entries(df)
    # Assume last TOC page is vaguely 1 for now, user can adjust
    mapped_entries = compute_page_mapping(entries, total_pdf_pages, 1)
    new_df = entries_to_dataframe(mapped_entries)
    summary = build_summary_markdown(mapped_entries)
    return new_df, summary

def prepare_split(df):
    entries = dataframe_to_entries(df)
    plan = generate_split_plan(entries)
    
    plan_data = []
    for item in plan:
        plan_data.append({
            "Enabled": item.enabled,
            "Title": item.title,
            "Start": item.start_page,
            "End": item.end_page,
            "Output": item.output_name,
            "Warnings": "; ".join(item.warnings)
        })
        
    return pd.DataFrame(plan_data)

def execute_split(pdf_file, split_df, prefix):
    if not pdf_file or split_df.empty:
        return None, "Missing PDF or split plan."
        
    # Reconstruct plan
    plan = []
    for _, row in split_df.iterrows():
        plan.append({
            "enabled": row.get("Enabled", True),
            "start_page": row.get("Start"),
            "end_page": row.get("End"),
            "output_name": row.get("Output")
        })
        
    try:
        files, zip_path = split_pdf(pdf_file.name, plan, prefix)
        return zip_path, f"✅ Successfully split into {len(files)} files. Download ZIP below."
    except Exception as e:
        return None, f"❌ Split failed: {str(e)}"

# Define UI
with gr.Blocks(title="PDF Cutter AI") as app:
    gr.Markdown("# ✂️ PDF Cutter AI\nSplit scanned PDFs by extracting Table of Contents using Vision LLMs.")
    
    # State variables
    total_pages_state = gr.State(0)
    image_paths_state = gr.State([])
    
    with gr.Tabs():
        with gr.Tab("1. Upload & Config"):
            with gr.Row():
                with gr.Column(scale=1):
                    pdf_upload = gr.File(label="Upload PDF Book", file_types=[".pdf"])
                    pdf_info_text = gr.Markdown("Please upload a PDF.")
                    toc_pages_input = gr.Textbox(label="TOC Page Ranges (e.g., 12-14, 16)", placeholder="e.g. 5-10")
                    extract_images_btn = gr.Button("Extract TOC Images", variant="primary")
                    
                with gr.Column(scale=1):
                    gr.Markdown("### API Configuration")
                    api_base = gr.Textbox(label="Base URL", value=Config.API_BASE_URL)
                    api_key = gr.Textbox(label="API Key", value=Config.API_KEY, type="password")
                    model_name = gr.Textbox(label="Model Name", value=Config.MODEL)
                    api_timeout = gr.Number(label="Timeout (s)", value=Config.TIMEOUT, precision=0)
                    sys_prompt = gr.Textbox(label="Custom System Prompt", value=Config.SYSTEM_PROMPT, lines=5)
                    
                    with gr.Row():
                        load_env_btn = gr.Button("Load defaults from .env")
                        test_conn_btn = gr.Button("Test API Connection")
                    conn_status = gr.Markdown()
                    
        with gr.Tab("2. TOC Preview"):
            gallery = gr.Gallery(label="TOC Pages Preview", columns=3)
            extract_info = gr.Markdown("No images extracted yet.")
            run_ai_btn = gr.Button("Run AI TOC Extraction", variant="primary", size="lg")
            
        with gr.Tab("3. Review & Edit"):
            with gr.Row():
                with gr.Column(scale=2):
                    gr.Markdown("### Edit Table of Contents")
                    toc_df = gr.Dataframe(
                        headers=["enabled", "level", "title", "printed_page", "page_number_type", "pdf_start_page", "pdf_end_page", "output_name", "warnings"],
                        datatype=["bool", "number", "str", "str", "str", "number", "number", "str", "str"],
                        interactive=True,
                        wrap=True
                    )
                    recompute_btn = gr.Button("Recompute Page Mapping", variant="secondary")
                    
                with gr.Column(scale=1):
                    summary_md = gr.Markdown("### Summary\nRun extraction first.")
                    with gr.Accordion("Raw JSON Response", open=False):
                        raw_json_view = gr.Code(language="json")
                        
        with gr.Tab("4. Split & Download"):
            gr.Markdown("### Final Split Plan")
            split_plan_df = gr.Dataframe(interactive=False, wrap=True)
            
            with gr.Row():
                prefix_input = gr.Textbox(label="Output Filename Prefix", value="chapter")
                split_btn = gr.Button("Split PDF & Create ZIP", variant="primary")
            
            split_result_md = gr.Markdown()
            download_file = gr.File(label="Download Split Archive")
            
    # Event wiring
    load_env_btn.click(
        load_env_defaults,
        outputs=[api_base, api_key, model_name, api_timeout, sys_prompt]
    )
    
    test_conn_btn.click(
        handle_test_conn,
        inputs=[api_base, api_key, model_name, api_timeout],
        outputs=[conn_status]
    )
    
    pdf_upload.upload(
        process_pdf_upload,
        inputs=[pdf_upload],
        outputs=[total_pages_state, pdf_info_text]
    )
    
    extract_images_btn.click(
        extract_images,
        inputs=[pdf_upload, toc_pages_input, total_pages_state],
        outputs=[image_paths_state, gallery, extract_info]
    )
    
    run_ai_btn.click(
        run_extraction,
        inputs=[image_paths_state, api_base, api_key, model_name, api_timeout, sys_prompt, total_pages_state],
        outputs=[raw_json_view, toc_df, summary_md]
    )
    
    recompute_btn.click(
        recompute_mapping,
        inputs=[toc_df, total_pages_state],
        outputs=[toc_df, summary_md]
    )
    
    # Whenever the review table is updated or mapping is recomputed, update the final split plan
    toc_df.change(
        prepare_split,
        inputs=[toc_df],
        outputs=[split_plan_df]
    )
    
    split_btn.click(
        execute_split,
        inputs=[pdf_upload, split_plan_df, prefix_input],
        outputs=[download_file, split_result_md]
    )

if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=7860)
