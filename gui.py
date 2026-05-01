import asyncio
import flet as ft
import os
import threading
from dotenv import load_dotenv
from typing import List

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
        self.page.title = "PDF Cutter AI"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.window.width = 1100
        self.page.window.height = 900
        self.page.padding = 20

        # State
        self.pdf_path: str | None = None
        self.total_pages: int = 0
        self.image_paths: List[str] = []
        self.toc_entries: List[TocEntry] = []
        self.raw_json: str = ""

        self.setup_ui()

    # ------------------------------------------------------------------ #
    #  UI BUILD                                                            #
    # ------------------------------------------------------------------ #

    def setup_ui(self):
        header = ft.Row(
            [
                ft.Icon(ft.Icons.CONTENT_CUT, size=30, color=ft.Colors.AMBER),
                ft.Text("PDF Cutter AI", size=28, weight=ft.FontWeight.BOLD),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
        )

        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            expand=True,
            tabs=[
                ft.Tab(
                    text="1. Config & Upload",
                    icon=ft.Icons.SETTINGS,
                    content=self._build_config_tab(),
                ),
                ft.Tab(
                    text="2. TOC Preview",
                    icon=ft.Icons.IMAGE,
                    content=self._build_preview_tab(),
                ),
                ft.Tab(
                    text="3. Review & Edit",
                    icon=ft.Icons.EDIT,
                    content=self._build_review_tab(),
                ),
                ft.Tab(
                    text="4. Split & Download",
                    icon=ft.Icons.SAVE,
                    content=self._build_split_tab(),
                ),
            ],
        )
        self.tabs = tabs

        self.page.add(
            ft.Column(
                [header, tabs],
                expand=True,
                spacing=12,
            )
        )

    # ---- Tab 1 -------------------------------------------------------- #

    def _build_config_tab(self) -> ft.Control:
        self.pdf_status = ft.Text("No PDF selected", color=ft.Colors.GREY_400)
        self.toc_range_input = ft.TextField(
            label="TOC Page Range (e.g. 12-14 or 5,6,7)",
            hint_text="12-14",
            expand=True,
        )
        self.api_base = ft.TextField(label="API Base URL", value=Config.API_BASE_URL, expand=True)
        self.api_key = ft.TextField(
            label="API Key",
            value=Config.API_KEY,
            password=True,
            can_reveal_password=True,
            expand=True,
        )
        self.model_name = ft.TextField(label="Model", value=Config.MODEL, expand=True)
        self.api_timeout = ft.TextField(
            label="Timeout (s)",
            value=str(Config.TIMEOUT),
            keyboard_type=ft.KeyboardType.NUMBER,
            width=120,
        )
        self.sys_prompt = ft.TextField(
            label="System Prompt (optional)",
            value=Config.SYSTEM_PROMPT,
            multiline=True,
            min_lines=3,
            max_lines=6,
            expand=True,
        )
        self.conn_status = ft.Text("")

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("Step 1: Select PDF & Configure API", size=18, weight=ft.FontWeight.W_600),
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                "Select PDF File",
                                icon=ft.Icons.UPLOAD_FILE,
                                on_click=self._pick_file,
                            ),
                            self.pdf_status,
                        ]
                    ),
                    self.toc_range_input,
                    ft.Divider(),
                    ft.Text("API Configuration", size=16, weight=ft.FontWeight.W_500),
                    self.api_base,
                    self.api_key,
                    ft.Row([self.model_name, self.api_timeout]),
                    self.sys_prompt,
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                "Test Connection",
                                icon=ft.Icons.WIFI,
                                on_click=self._test_connection,
                            ),
                            ft.OutlinedButton(
                                "Load from .env",
                                icon=ft.Icons.REFRESH,
                                on_click=self._load_env,
                            ),
                        ]
                    ),
                    self.conn_status,
                ],
                scroll=ft.ScrollMode.AUTO,
                spacing=16,
            ),
            padding=20,
        )

    # ---- Tab 2 -------------------------------------------------------- #

    def _build_preview_tab(self) -> ft.Control:
        self.gallery = ft.Row(wrap=True, scroll=ft.ScrollMode.AUTO, expand=True)
        self.preview_info = ft.Text("Upload a PDF and select TOC pages in Step 1 first.")

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("Step 2: Preview TOC Pages & Run AI", size=18, weight=ft.FontWeight.W_600),
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                "Extract TOC Images",
                                icon=ft.Icons.IMAGE_SEARCH,
                                on_click=self._extract_images,
                            ),
                            ft.FilledButton(
                                "Run AI TOC Extraction",
                                icon=ft.Icons.AUTO_AWESOME,
                                on_click=self._run_extraction,
                            ),
                        ]
                    ),
                    self.preview_info,
                    ft.Container(
                        self.gallery,
                        height=420,
                        border=ft.border.all(1, ft.Colors.GREY_700),
                        border_radius=10,
                        padding=10,
                        expand=False,
                    ),
                ],
                spacing=16,
            ),
            padding=20,
        )

    # ---- Tab 3 -------------------------------------------------------- #

    def _build_review_tab(self) -> ft.Control:
        self.entries_list = ft.ListView(expand=True, spacing=6)
        self.summary_text = ft.Markdown("*No data yet.*", expand=True)

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("Step 3: Review & Edit TOC Entries", size=18, weight=ft.FontWeight.W_600),
                    ft.Row(
                        [
                            ft.ElevatedButton(
                                "Recompute Mapping",
                                icon=ft.Icons.REFRESH,
                                on_click=self._recompute,
                            ),
                            ft.OutlinedButton(
                                "Add Row",
                                icon=ft.Icons.ADD,
                                on_click=self._add_row,
                            ),
                        ]
                    ),
                    ft.Row(
                        [
                            ft.Container(
                                content=self.entries_list,
                                expand=3,
                                height=520,
                                border=ft.border.all(1, ft.Colors.GREY_700),
                                border_radius=10,
                                padding=8,
                            ),
                            ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Text("Summary", size=16, weight=ft.FontWeight.BOLD),
                                        self.summary_text,
                                    ],
                                    scroll=ft.ScrollMode.AUTO,
                                ),
                                expand=1,
                                height=520,
                                padding=12,
                                bgcolor=ft.Colors.GREY_900,
                                border_radius=10,
                            ),
                        ],
                        expand=True,
                    ),
                ],
                spacing=16,
            ),
            padding=20,
        )

    # ---- Tab 4 -------------------------------------------------------- #

    def _build_split_tab(self) -> ft.Control:
        self.split_plan_view = ft.ListView(expand=True, spacing=4)
        self.prefix_input = ft.TextField(label="Filename Prefix", value="chapter", width=260)
        self.progress_ring = ft.ProgressRing(visible=False, width=24, height=24)
        self.split_status = ft.Text("")

        return ft.Container(
            content=ft.Column(
                [
                    ft.Text("Step 4: Execute Split", size=18, weight=ft.FontWeight.W_600),
                    ft.Text("Confirm the split plan below, then click Split."),
                    ft.Container(
                        self.split_plan_view,
                        height=400,
                        border=ft.border.all(1, ft.Colors.GREY_700),
                        border_radius=10,
                        padding=8,
                    ),
                    ft.Row(
                        [
                            self.prefix_input,
                            ft.FilledButton(
                                "Split PDF & Save",
                                icon=ft.Icons.CONTENT_CUT,
                                on_click=self._split_pdf,
                            ),
                            self.progress_ring,
                        ]
                    ),
                    self.split_status,
                ],
                spacing=16,
            ),
            padding=20,
        )

    # ------------------------------------------------------------------ #
    #  EVENT HANDLERS                                                      #
    # ------------------------------------------------------------------ #

    async def _pick_file(self, e):
        """Open file picker dialog using Flet 0.80+ async API."""
        files = await ft.FilePicker().pick_files(allowed_extensions=["pdf"])
        if files:
            self.pdf_path = files[0].path
            self.total_pages = get_pdf_info(self.pdf_path)
            self.pdf_status.value = (
                f"\u2705 {os.path.basename(self.pdf_path)}  ({self.total_pages} pages)"
            )
        else:
            self.pdf_status.value = "No file selected."
        self.page.update()

    def _load_env(self, _):
        load_dotenv(override=True)
        self.api_base.value = os.getenv("PDFCUTTER_API_BASE_URL", Config.API_BASE_URL)
        self.api_key.value = os.getenv("PDFCUTTER_API_KEY", "")
        self.model_name.value = os.getenv("PDFCUTTER_MODEL", Config.MODEL)
        self.api_timeout.value = os.getenv("PDFCUTTER_TIMEOUT", str(Config.TIMEOUT))
        self.sys_prompt.value = os.getenv("PDFCUTTER_SYSTEM_PROMPT", Config.SYSTEM_PROMPT)
        self.page.update()

    def _test_connection(self, _):
        self.conn_status.value = "Testing..."
        self.page.update()

        def run():
            try:
                ok = test_connection(
                    self.api_base.value,
                    self.api_key.value,
                    self.model_name.value,
                    int(self.api_timeout.value or "30"),
                )
                self.conn_status.value = "\u2705 Connection successful!" if ok else "\u274c Connection failed."
                self.conn_status.color = ft.Colors.GREEN if ok else ft.Colors.RED
            except Exception as exc:
                self.conn_status.value = f"\u274c {exc}"
                self.conn_status.color = ft.Colors.RED
            self.page.update()

        threading.Thread(target=run, daemon=True).start()

    def _extract_images(self, _):
        if not self.pdf_path:
            self.preview_info.value = "\u274c Please select a PDF first."
            self.page.update()
            return
        if not self.toc_range_input.value.strip():
            self.preview_info.value = "\u274c Please enter TOC page range."
            self.page.update()
            return

        try:
            pages = parse_page_range(self.toc_range_input.value, self.total_pages)
            self.image_paths = extract_toc_images(self.pdf_path, pages)

            self.gallery.controls.clear()
            for img_path in self.image_paths:
                self.gallery.controls.append(
                    ft.Image(
                        src=img_path,
                        width=180,
                        height=260,
                        fit=ft.ImageFit.CONTAIN,
                        border_radius=8,
                    )
                )
            self.preview_info.value = f"\u2705 Extracted {len(self.image_paths)} TOC page image(s)."
        except Exception as exc:
            self.preview_info.value = f"\u274c {exc}"
        self.page.update()

    def _run_extraction(self, _):
        if not self.image_paths:
            self.preview_info.value = "\u274c Extract TOC images first."
            self.page.update()
            return

        self.preview_info.value = "\U0001f916 AI is thinking\u2026 please wait."
        self.page.update()

        def run():
            try:
                raw_text = extract_toc_from_images(
                    self.image_paths,
                    self.api_base.value,
                    self.api_key.value,
                    self.model_name.value,
                    int(self.api_timeout.value or "30"),
                    self.sys_prompt.value,
                )
                self.raw_json = raw_text
                result = parse_extraction_result(raw_text, [1], self.model_name.value)
                self.toc_entries = compute_page_mapping(
                    result.entries, self.total_pages, 1
                )
                self._refresh_review_ui()
                self.tabs.selected_index = 2
                self.preview_info.value = "\u2705 Extraction complete! Review entries in Step 3."
            except Exception as exc:
                self.preview_info.value = f"\u274c {exc}"
            self.page.update()

        threading.Thread(target=run, daemon=True).start()

    # ------------------------------------------------------------------ #
    #  REVIEW UI                                                           #
    # ------------------------------------------------------------------ #

    def _refresh_review_ui(self):
        self.entries_list.controls.clear()

        # Column header
        self.entries_list.controls.append(
            ft.Row(
                [
                    ft.Text("\u2713", width=32, weight=ft.FontWeight.BOLD),
                    ft.Text("Lv", width=36, weight=ft.FontWeight.BOLD),
                    ft.Text("Title", expand=True, weight=ft.FontWeight.BOLD),
                    ft.Text("Pg", width=56, weight=ft.FontWeight.BOLD),
                    ft.Text("Type", width=80, weight=ft.FontWeight.BOLD),
                    ft.Text("PDF\u2192", width=60, weight=ft.FontWeight.BOLD),
                    ft.Text("", width=40),
                ],
                spacing=4,
            )
        )

        for i, entry in enumerate(self.toc_entries):
            row = ft.Row(
                [
                    ft.Checkbox(
                        value=entry.enabled,
                        on_change=lambda e, idx=i: self._update_field(idx, "enabled", e.control.value),
                    ),
                    ft.TextField(
                        value=str(entry.level),
                        width=40,
                        dense=True,
                        on_change=lambda e, idx=i: self._update_field(idx, "level", e.control.value),
                    ),
                    ft.TextField(
                        value=entry.title,
                        expand=True,
                        dense=True,
                        on_change=lambda e, idx=i: self._update_field(idx, "title", e.control.value),
                    ),
                    ft.TextField(
                        value=str(entry.printed_page or ""),
                        width=56,
                        dense=True,
                        on_change=lambda e, idx=i: self._update_field(idx, "printed_page", e.control.value),
                    ),
                    ft.Dropdown(
                        value=entry.page_number_type,
                        width=80,
                        dense=True,
                        options=[
                            ft.dropdown.Option("arabic"),
                            ft.dropdown.Option("roman"),
                            ft.dropdown.Option("unknown"),
                        ],
                        on_change=lambda e, idx=i: self._update_field(idx, "page_number_type", e.control.value),
                    ),
                    ft.TextField(
                        value=str(entry.pdf_start_page or ""),
                        width=60,
                        dense=True,
                        on_change=lambda e, idx=i: self._update_field(idx, "pdf_start_page", e.control.value),
                    ),
                    ft.IconButton(
                        ft.Icons.DELETE_OUTLINE,
                        icon_color=ft.Colors.RED_300,
                        tooltip="Delete row",
                        on_click=lambda _, idx=i: self._delete_row(idx),
                    ),
                ],
                spacing=4,
            )
            bg = ft.Colors.ORANGE_900 if entry.warnings else None
            self.entries_list.controls.append(
                ft.Container(
                    content=row,
                    bgcolor=bg,
                    border_radius=6,
                    padding=ft.padding.symmetric(vertical=2),
                )
            )

        self.summary_text.value = build_summary_markdown(self.toc_entries)
        self._refresh_split_plan()
        self.page.update()

    def _update_field(self, idx: int, field: str, value):
        entry = self.toc_entries[idx]
        if field == "enabled":
            entry.enabled = bool(value)
        elif field == "level":
            entry.level = int(value) if str(value).isdigit() else 1
        elif field == "title":
            entry.title = str(value)
        elif field == "printed_page":
            entry.printed_page = value
        elif field == "page_number_type":
            entry.page_number_type = value
        elif field == "pdf_start_page":
            entry.pdf_start_page = int(value) if str(value).isdigit() else None

    def _delete_row(self, idx: int):
        self.toc_entries.pop(idx)
        self._refresh_review_ui()

    def _add_row(self, _):
        self.toc_entries.append(TocEntry(level=1, title="New Entry", page_number_type="arabic"))
        self._refresh_review_ui()

    def _recompute(self, _):
        self.toc_entries = compute_page_mapping(self.toc_entries, self.total_pages, 1)
        self._refresh_review_ui()

    # ------------------------------------------------------------------ #
    #  SPLIT PLAN                                                          #
    # ------------------------------------------------------------------ #

    def _refresh_split_plan(self):
        self.split_plan_view.controls.clear()
        plan = generate_split_plan(self.toc_entries)
        if not plan:
            self.split_plan_view.controls.append(
                ft.Text("No entries yet.", color=ft.Colors.GREY_400)
            )
            return
        for item in plan:
            warn_icon = (
                ft.Icon(ft.Icons.WARNING_AMBER, color=ft.Colors.ORANGE, size=18)
                if item.warnings
                else None
            )
            self.split_plan_view.controls.append(
                ft.ListTile(
                    title=ft.Text(item.title),
                    subtitle=ft.Text(
                        f"PDF pages {item.start_page}\u2013{item.end_page}  \u2192  {item.output_name}.pdf"
                    ),
                    trailing=warn_icon,
                )
            )

    def _split_pdf(self, _):
        if not self.pdf_path:
            self.split_status.value = "\u274c No PDF loaded."
            self.page.update()
            return

        self.progress_ring.visible = True
        self.split_status.value = "Splitting\u2026 please wait."
        self.page.update()

        def run():
            try:
                plan = generate_split_plan(self.toc_entries)
                plan_dicts = [
                    {
                        "enabled": p.enabled,
                        "start_page": p.start_page,
                        "end_page": p.end_page,
                        "output_name": p.output_name,
                    }
                    for p in plan
                ]
                files, zip_path = split_pdf(self.pdf_path, plan_dicts, self.prefix_input.value)
                self.split_status.value = (
                    f"\u2705 Done! Saved {len(files)} file(s).\nZIP: {zip_path}"
                )
                self.split_status.color = ft.Colors.GREEN
            except Exception as exc:
                self.split_status.value = f"\u274c {exc}"
                self.split_status.color = ft.Colors.RED
            self.progress_ring.visible = False
            self.page.update()

        threading.Thread(target=run, daemon=True).start()


async def main(page: ft.Page):
    PDFCutterGUI(page)


if __name__ == "__main__":
    ft.run(main)
