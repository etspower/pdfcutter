import flet as ft
import os
import json
import pandas as pd
from dotenv import load_dotenv
from typing import List, Optional

from src.config import Config
from src.pdf_utils import get_pdf_info, parse_page_range, extract_toc_images, split_pdf
from src.llm_client import test_connection, extract_toc_from_images
from src.toc_extract import parse_extraction_result
from src.split_logic import compute_page_mapping, generate_split_plan
from src.ui_helpers import build_summary_markdown
from src.schemas import TocEntry

class PDFCutterGUI:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "PDF Cutter AI - Desktop"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.window.width = 1100
        self.page.window.height = 900
        self.page.padding = 20
        
        # State
        self.pdf_path = None
        self.total_pages = 0
        self.image_paths = []
        self.toc_entries: List[TocEntry] = []
        self.raw_json = ""
        
        # UI Components
        self.setup_ui()

    def setup_ui(self):
        # Header
        header = ft.Row(
            [
                ft.Icon("content_cut", size=30, color=ft.Colors.AMBER),
                ft.Text("PDF Cutter AI", size=32, weight=ft.FontWeight.BOLD),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
        )

        # File Picker
        self.file_picker = ft.FilePicker()
        self.page.overlay.append(self.file_picker)

        # Tab 1: Config
        self.tab_config = self.create_config_tab()
        
        # Tab 2: Preview
        self.tab_preview = self.create_preview_tab()
        
        # Tab 3: Review
        self.tab_review = self.create_review_tab()
        
        # Tab 4: Split
        self.tab_split = self.create_split_tab()

        self.tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(text="1. Config", icon="settings", content=self.tab_config),
                ft.Tab(text="2. Preview", icon="image", content=self.tab_preview),
                ft.Tab(text="3. Review", icon="edit", content=self.tab_review),
                ft.Tab(text="4. Split", icon="save", content=self.tab_split),
            ],
            expand=1,
        )

        self.page.add(header, self.tabs)

    def create_config_tab(self):
        self.pdf_status = ft.Text("No PDF selected", color=ft.Colors.GREY_400)
        self.toc_range_input = ft.TextField(label="TOC Page Ranges (e.g., 12-14, 16)", hint_text="5-10")
        
        self.api_base = ft.TextField(label="Base URL", value=Config.API_BASE_URL)
        self.api_key = ft.TextField(label="API Key", value=Config.API_KEY, password=True, can_reveal_password=True)
        self.model_name = ft.TextField(label="Model Name", value=Config.MODEL)
        self.api_timeout = ft.TextField(label="Timeout (s)", value=str(Config.TIMEOUT), keyboard_type=ft.KeyboardType.NUMBER)
        self.sys_prompt = ft.TextField(label="Custom System Prompt", value=Config.SYSTEM_PROMPT, multiline=True, min_lines=3, max_lines=5)
        
        self.conn_status = ft.Text("")

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("Step 1: Select PDF & API Settings", size=20, weight=ft.FontWeight.W_600),
                    ft.Row([
                        ft.Button("Select PDF File", icon="upload_file", on_click=self.pick_pdf_clicked),
                        self.pdf_status
                    ]),
                    self.toc_range_input,
                    ft.Divider(),
                    ft.Text("API Configuration", size=18, weight=ft.FontWeight.W_500),
                    self.api_base,
                    self.api_key,
                    self.model_name,
                    ft.Row([self.api_timeout]),
                    self.sys_prompt,
                    ft.Row([
                        ft.Button("Test Connection", on_click=self.test_api_connection),
                        ft.Button("Load from .env", on_click=self.load_env_to_ui),
                    ]),
                    self.conn_status
                ],
                scroll=ft.ScrollMode.AUTO,
                spacing=20
            ),
            padding=20
        )

    def create_preview_tab(self):
        self.gallery = ft.Row(wrap=True, scroll=ft.ScrollMode.AUTO, expand=True)
        self.preview_info = ft.Text("")
        
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("Step 2: Preview TOC Pages", size=20, weight=ft.FontWeight.W_600),
                    ft.Row([
                        ft.Button("Extract TOC Images", icon="image_search", on_click=self.extract_images_clicked),
                        self.preview_info
                    ]),
                    ft.Container(self.gallery, height=400, border=ft.Border.all(1, ft.Colors.GREY_700), border_radius=10, padding=10),
                    ft.Button("Run AI TOC Extraction", icon="auto_awesome", color=ft.Colors.WHITE, bgcolor=ft.Colors.BLUE_700, height=50, on_click=self.run_extraction_clicked),
                ],
                spacing=20
            ),
            padding=20
        )

    def create_review_tab(self):
        self.entries_list = ft.ListView(expand=True, spacing=10)
        self.summary_text = ft.Markdown("")
        
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("Step 3: Review & Edit TOC", size=20, weight=ft.FontWeight.W_600),
                    ft.Row([
                        ft.Button("Recompute Mapping", icon="refresh", on_click=self.recompute_clicked),
                        ft.Button("Add Row", icon="add", on_click=self.add_row_clicked),
                    ]),
                    ft.Row([
                        ft.Container(self.entries_list, expand=3, height=500, border=ft.Border.all(1, ft.Colors.GREY_700), border_radius=10),
                        ft.Container(ft.Column([ft.Text("Summary", size=18, weight="bold"), self.summary_text], scroll=ft.ScrollMode.AUTO), expand=1, height=500, padding=10, bgcolor=ft.Colors.GREY_900, border_radius=10)
                    ], expand=True)
                ],
                spacing=20
            ),
            padding=20
        )

    def create_split_tab(self):
        self.split_plan_view = ft.ListView(expand=True, spacing=5)
        self.prefix_input = ft.TextField(label="Filename Prefix", value="chapter", width=300)
        self.progress_bar = ft.ProgressBar(width=400, visible=False)
        self.split_status = ft.Text("")

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("Step 4: Execute Split", size=20, weight=ft.FontWeight.W_600),
                    ft.Text("Review the final plan below before processing."),
                    ft.Container(self.split_plan_view, height=400, border=ft.Border.all(1, ft.Colors.GREY_700), border_radius=10),
                    ft.Row([
                        self.prefix_input,
                        ft.Button("Split PDF & Save", icon="content_cut", bgcolor=ft.Colors.GREEN_700, height=50, on_click=self.split_clicked)
                    ]),
                    self.progress_bar,
                    self.split_status
                ],
                spacing=20
            ),
            padding=20
        )

    # Event Handlers
    async def pick_pdf_clicked(self, e):
        files = await self.file_picker.pick_files()
        if files:
            self.pdf_path = files[0].path
            self.total_pages = get_pdf_info(self.pdf_path)
            self.pdf_status.value = f"Selected: {os.path.basename(self.pdf_path)} ({self.total_pages} pages)"
            self.page.update()

    def load_env_to_ui(self, _):
        load_dotenv(override=True)
        self.api_base.value = os.getenv("PDFCUTTER_API_BASE_URL", Config.API_BASE_URL)
        self.api_key.value = os.getenv("PDFCUTTER_API_KEY", "")
        self.model_name.value = os.getenv("PDFCUTTER_MODEL", Config.MODEL)
        self.api_timeout.value = os.getenv("PDFCUTTER_TIMEOUT", str(Config.TIMEOUT))
        self.sys_prompt.value = os.getenv("PDFCUTTER_SYSTEM_PROMPT", Config.SYSTEM_PROMPT)
        self.page.update()

    def test_api_connection(self, _):
        try:
            success = test_connection(self.api_base.value, self.api_key.value, self.model_name.value, int(self.api_timeout.value))
            if success:
                self.conn_status.value = "✅ Connection successful!"
                self.conn_status.color = ft.Colors.GREEN
        except Exception as e:
            self.conn_status.value = f"❌ Error: {str(e)}"
            self.conn_status.color = ft.Colors.RED
        self.page.update()

    def extract_images_clicked(self, _):
        if not self.pdf_path or not self.toc_range_input.value:
            self.preview_info.value = "Error: PDF or Range missing"
            self.page.update()
            return
            
        pages = parse_page_range(self.toc_range_input.value, self.total_pages)
        self.image_paths = extract_toc_images(self.pdf_path, pages)
        
        self.gallery.controls.clear()
        for img_path in self.image_paths:
            self.gallery.controls.append(
                ft.Image(src=img_path, width=200, height=280, fit=ft.ImageFit.CONTAIN, border_radius=10)
            )
        self.preview_info.value = f"Extracted {len(self.image_paths)} images."
        self.page.update()

    def run_extraction_clicked(self, _):
        if not self.image_paths:
            return
            
        self.preview_info.value = "AI is thinking... please wait."
        self.page.update()
        
        try:
            raw_text = extract_toc_from_images(
                self.image_paths, 
                self.api_base.value, 
                self.api_key.value, 
                self.model_name.value, 
                int(self.api_timeout.value), 
                self.sys_prompt.value
            )
            self.raw_json = raw_text
            
            result = parse_extraction_result(raw_text, [1], self.model_name.value)
            # Initial mapping
            self.toc_entries = compute_page_mapping(result.entries, self.total_pages, 1)
            self.refresh_review_ui()
            self.tabs.selected_index = 2
            self.preview_info.value = "Extraction complete!"
        except Exception as e:
            self.preview_info.value = f"Error: {str(e)}"
        self.page.update()

    def refresh_review_ui(self):
        self.entries_list.controls.clear()
        
        # Header Row
        self.entries_list.controls.append(ft.Row([
            ft.Text("En", width=30), ft.Text("Lvl", width=30), ft.Text("Title", expand=True), 
            ft.Text("PrntPg", width=60), ft.Text("Type", width=60), ft.Text("PDF Start", width=60)
        ]))

        for i, entry in enumerate(self.toc_entries):
            row = ft.Row([
                ft.Checkbox(value=entry.enabled, on_change=lambda e, idx=i: self.update_entry_field(idx, "enabled", e.control.value)),
                ft.TextField(value=str(entry.level), width=40, dense=True, on_change=lambda e, idx=i: self.update_entry_field(idx, "level", e.control.value)),
                ft.TextField(value=entry.title, expand=True, dense=True, on_change=lambda e, idx=i: self.update_entry_field(idx, "title", e.control.value)),
                ft.TextField(value=str(entry.printed_page or ""), width=60, dense=True, on_change=lambda e, idx=i: self.update_entry_field(idx, "printed_page", e.control.value)),
                ft.Dropdown(value=entry.page_number_type, width=80, dense=True, options=[
                    ft.dropdown.Option("arabic"), ft.dropdown.Option("roman"), ft.dropdown.Option("unknown")
                ], on_change=lambda e, idx=i: self.update_entry_field(idx, "page_number_type", e.control.value)),
                ft.TextField(value=str(entry.pdf_start_page or ""), width=60, dense=True, on_change=lambda e, idx=i: self.update_entry_field(idx, "pdf_start_page", e.control.value)),
                ft.IconButton("delete", icon_color=ft.Colors.RED_400, on_click=lambda _, idx=i: self.delete_row(idx))
            ])
            self.entries_list.controls.append(row)
        
        self.summary_text.value = build_summary_markdown(self.toc_entries)
        self.update_split_plan_view()
        self.page.update()

    def update_entry_field(self, idx, field, value):
        entry = self.toc_entries[idx]
        if field == "enabled": entry.enabled = value
        elif field == "level": entry.level = int(value) if value.isdigit() else 1
        elif field == "title": entry.title = value
        elif field == "printed_page": entry.printed_page = value
        elif field == "page_number_type": entry.page_number_type = value
        elif field == "pdf_start_page": entry.pdf_start_page = int(value) if value.isdigit() else None

    def delete_row(self, idx):
        self.toc_entries.pop(idx)
        self.refresh_review_ui()

    def add_row_clicked(self, _):
        self.toc_entries.append(TocEntry(level=1, title="New Entry", page_number_type="arabic"))
        self.refresh_review_ui()

    def recompute_clicked(self, _):
        self.toc_entries = compute_page_mapping(self.toc_entries, self.total_pages, 1)
        self.refresh_review_ui()

    def update_split_plan_view(self):
        self.split_plan_view.controls.clear()
        plan = generate_split_plan(self.toc_entries)
        for item in plan:
            self.split_plan_view.controls.append(
                ft.ListTile(
                    title=ft.Text(item.title),
                    subtitle=ft.Text(f"Pages: {item.start_page} to {item.end_page} -> {item.output_name}.pdf"),
                    trailing=ft.Icon("warning", color="orange") if item.warnings else None
                )
            )

    def split_clicked(self, _):
        if not self.pdf_path: return
        
        self.progress_bar.visible = True
        self.split_status.value = "Splitting PDF... please wait."
        self.page.update()
        
        try:
            plan_dicts = []
            plan = generate_split_plan(self.toc_entries)
            for p in plan:
                plan_dicts.append({
                    "enabled": p.enabled,
                    "start_page": p.start_page,
                    "end_page": p.end_page,
                    "output_name": p.output_name
                })
                
            files, zip_path = split_pdf(self.pdf_path, plan_dicts, self.prefix_input.value)
            self.split_status.value = f"✅ Success! Saved {len(files)} files and ZIP to 'output/' folder.\nZIP: {zip_path}"
            self.split_status.color = ft.Colors.GREEN
        except Exception as e:
            self.split_status.value = f"❌ Error: {str(e)}"
            self.split_status.color = ft.Colors.RED
            
        self.progress_bar.visible = False
        self.page.update()

def main(page: ft.Page):
    PDFCutterGUI(page)

if __name__ == "__main__":
    ft.run(main)
