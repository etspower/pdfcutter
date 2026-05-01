import flet as ft
import os
import threading
import traceback
from datetime import datetime
from importlib.metadata import version as pkg_version, PackageNotFoundError
from dotenv import load_dotenv
from typing import List

from src.config import Config
from src.pdf_utils import get_pdf_info, parse_page_range, extract_toc_images, split_pdf
from src.llm_client import test_connection, extract_toc_from_images
from src.toc_extract import parse_extraction_result
from src.split_logic import compute_page_mapping, generate_split_plan
from src.ui_helpers import build_summary_markdown
from src.schemas import TocEntry

try:
    _FLET_VER = pkg_version("flet")
except PackageNotFoundError:
    _FLET_VER = "unknown"


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
    #  LOGGING                                                             #
    # ------------------------------------------------------------------ #

    def _log(self, msg: str, level: str = "INFO"):
        ts = datetime.now().strftime("%H:%M:%S")
        colors = {
            "INFO": ft.Colors.CYAN_200,
            "OK": ft.Colors.GREEN_300,
            "WARN": ft.Colors.AMBER_300,
            "ERROR": ft.Colors.RED_300,
        }
        color = colors.get(level, ft.Colors.WHITE)
        self.log_list.controls.append(
            ft.Text(
                f"[{ts}] [{level}] {msg}",
                color=color,
                size=12,
                font_family="monospace",
                selectable=True,
            )
        )
        if len(self.log_list.controls) > 200:
            self.log_list.controls.pop(0)
        self.page.update()

    # ------------------------------------------------------------------ #
    #  UI BUILD                                                            #
    # ------------------------------------------------------------------ #

    def setup_ui(self):
        self.log_list = ft.ListView(expand=True, spacing=1, auto_scroll=True)
        log_panel = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("\U0001f4cb Log", weight=ft.FontWeight.BOLD, size=13),
                            ft.TextButton("Clear", on_click=lambda _: self._clear_log()),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Container(
                        self.log_list,
                        height=130,
                        bgcolor=ft.Colors.GREY_900,
                        border_radius=8,
                        padding=8,
                        border=ft.Border.all(1, ft.Colors.GREY_700),
                    ),
                ],
                spacing=4,
            ),
            padding=ft.Padding.only(top=8),
        )

        header = ft.Row(
            [
                ft.Icon(ft.Icons.CONTENT_CUT, size=30, color=ft.Colors.AMBER),
                ft.Text("PDF Cutter AI", size=28, weight=ft.FontWeight.BOLD),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
        )

        tab1_content = self._build_config_tab()
        tab2_content = self._build_preview_tab()
        tab3_content = self._build_review_tab()
        tab4_content = self._build_split_tab()

        self.tab_bar = ft.TabBar(
            tabs=[
                ft.Tab(label="1. Config & Upload", icon=ft.Icons.SETTINGS),
                ft.Tab(label="2. TOC Preview", icon=ft.Icons.IMAGE),
                ft.Tab(label="3. Review & Edit", icon=ft.Icons.EDIT),
                ft.Tab(label="4. Split & Download", icon=ft.Icons.SAVE),
            ],
        )

        self.tab_view = ft.TabBarView(
            expand=True,
            controls=[tab1_content, tab2_content, tab3_content, tab4_content],
        )

        self.tabs = ft.Tabs(
            length=4,
            selected_index=0,
            animation_duration=ft.Duration(milliseconds=300),
            expand=True,
            content=ft.Column(
                expand=True,
                controls=[self.tab_bar, self.tab_view],
            ),
        )

        self.page.add(
            ft.Column(
                [header, self.tabs, log_panel],
                expand=True,
                spacing=12,
            )
        )
        self._log(f"App started. Flet version: {_FLET_VER}")

    def _clear_log(self):
        self.log_list.controls.clear()
        self.page.update()

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
                            ft.Button(
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
                            ft.Button(
                                "Test Connection",
                                icon=ft.Icons.WIFI,
                                on_click=self._test_connection,
                            ),
                            ft.Button(
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
                            ft.Button(
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
                        border=ft.Border.all(1, ft.Colors.GREY_700),
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
                            ft.Button(
                                "Recompute Mapping",
                                icon=ft.Icons.REFRESH,
                                on_click=self._recompute,
                            ),
                            ft.Button(
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
                                border=ft.Border.all(1, ft.Colors.GREY_700),
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
                        border=ft.Border.all(1, ft.Colors.GREY_700),
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
        self._log("Opening file picker\u2026")
        try:
            result = await ft.FilePicker().pick_files(allowed_extensions=["pdf"])
            if result:
                self.pdf_path = result[0].path
                self._log(f"Reading page count: {self.pdf_path}")
                self.total_pages = get_pdf_info(self.pdf_path)
                self.pdf_status.value = (
                    f"\u2705 {os.path.basename(self.pdf_path)}  ({self.total_pages} pages)"
                )
                self._log(f"Loaded: {os.path.basename(self.pdf_path)}, {self.total_pages} pages", "OK")
            else:
                self.pdf_status.value = "No file selected."
                self._log("File picker cancelled.", "WARN")
        except Exception as exc:
            self._log(f"_pick_file error: {exc}\n{traceback.format_exc()}", "ERROR")
        self.page.update()

    def _load_env(self, _):
        self._log("Loading config from .env\u2026")
        load_dotenv(override=True)
        self.api_base.value = os.getenv("PDFCUTTER_API_BASE_URL", Config.API_BASE_URL)
        self.api_key.value = os.getenv("PDFCUTTER_API_KEY", "")
        self.model_name.value = os.getenv("PDFCUTTER_MODEL", Config.MODEL)
        self.api_timeout.value = os.getenv("PDFCUTTER_TIMEOUT", str(Config.TIMEOUT))
        self.sys_prompt.value = os.getenv("PDFCUTTER_SYSTEM_PROMPT", Config.SYSTEM_PROMPT)
        self._log("Config reloaded from .env", "OK")
        self.page.update()

    def _test_connection(self, _):
        self.conn_status.value = "Testing..."
        self._log(f"Testing connection to {self.api_base.value} model={self.model_name.value}")
        self.page.update()

        def run():
            try:
                ok = test_connection(
                    self.api_base.value,
                    self.api_key.value,
                    self.model_name.value,
                    int(self.api_timeout.value or "30"),
                )
                if ok:
                    self.conn_status.value = "\u2705 Connection successful!"
                    self.conn_status.color = ft.Colors.GREEN
                    self._log("Connection test passed.", "OK")
                else:
                    self.conn_status.value = "\u274c Connection failed."
                    self.conn_status.color = ft.Colors.RED
                    self._log("Connection test returned False.", "WARN")
            except Exception as exc:
                self.conn_status.value = f"\u274c {exc}"
                self.conn_status.color = ft.Colors.RED
                self._log(f"Connection error: {exc}\n{traceback.format_exc()}", "ERROR")
            self.page.update()

        threading.Thread(target=run, daemon=True).start()

    def _extract_images(self, _):
        if not self.pdf_path:
            self.preview_info.value = "\u274c Please select a PDF first."
            self._log("Extract aborted: no PDF selected.", "WARN")
            self.page.update()
            return
        if not self.toc_range_input.value.strip():
            self.preview_info.value = "\u274c Please enter TOC page range."
            self._log("Extract aborted: no page range.", "WARN")
            self.page.update()
            return

        try:
            self._log(f"Parsing page range: '{self.toc_range_input.value}'")
            pages = parse_page_range(self.toc_range_input.value, self.total_pages)
            self._log(f"Pages to render: {pages}")

            self._log("Rendering pages with PyMuPDF\u2026")
            self.image_paths = extract_toc_images(self.pdf_path, pages)
            self._log(f"Rendered {len(self.image_paths)} image(s): {self.image_paths}", "OK")

            self.gallery.controls.clear()
            for img_path in self.image_paths:
                self.gallery.controls.append(
                    ft.Image(
                        src=img_path,
                        width=180,
                        height=260,
                        fit="contain",
                        border_radius=8,
                    )
                )
            self.preview_info.value = f"\u2705 Extracted {len(self.image_paths)} TOC page image(s)."
        except Exception as exc:
            self.preview_info.value = f"\u274c {exc}"
            self._log(f"extract_images error: {exc}\n{traceback.format_exc()}", "ERROR")
        self.page.update()

    def _run_extraction(self, _):
        if not self.image_paths:
            self.preview_info.value = "\u274c Extract TOC images first."
            self._log("AI extraction aborted: no images.", "WARN")
            self.page.update()
            return

        self.preview_info.value = "\U0001f916 AI is thinking\u2026 please wait."
        self._log(f"Sending {len(self.image_paths)} image(s) to AI model={self.model_name.value}\u2026")
        self.page.update()

        def run():
            try:
                self._log("Calling extract_toc_from_images\u2026")
                raw_text = extract_toc_from_images(
                    self.image_paths,
                    self.api_base.value,
                    self.api_key.value,
                    self.model_name.value,
                    int(self.api_timeout.value or "30"),
                    self.sys_prompt.value,
                )
                self._log(f"AI raw response length: {len(raw_text)} chars")
                self.raw_json = raw_text

                self._log("Parsing extraction result\u2026")
                result = parse_extraction_result(raw_text, [1], self.model_name.value)
                self._log(f"Parsed {len(result.entries)} TOC entries.")

                self._log("Computing page mapping\u2026")
                self.toc_entries = compute_page_mapping(
                    result.entries, self.total_pages, 1
                )
                self._log(f"Page mapping done. {len(self.toc_entries)} entries.", "OK")

                self._refresh_review_ui()
                self.tabs.selected_index = 2
                self.preview_info.value = "\u2705 Extraction complete! Review entries in Step 3."
            except Exception as exc:
                self.preview_info.value = f"\u274c {exc}"
                self._log(f"AI extraction error: {exc}\n{traceback.format_exc()}", "ERROR")
            self.page.update()

        threading.Thread(target=run, daemon=True).start()

    # ------------------------------------------------------------------ #
    #  REVIEW UI                                                           #
    # ------------------------------------------------------------------ #

    def _refresh_review_ui(self):
        self.entries_list.controls.clear()

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
                            ft.DropdownOption(key="arabic"),
                            ft.DropdownOption(key="roman"),
                            ft.DropdownOption(key="unknown"),
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
                    padding=ft.Padding.symmetric(vertical=2),
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
        self._log(f"Deleted row {idx}")
        self.toc_entries.pop(idx)
        self._refresh_review_ui()

    def _add_row(self, _):
        self._log("Added new empty row.")
        self.toc_entries.append(TocEntry(level=1, title="New Entry", page_number_type="arabic"))
        self._refresh_review_ui()

    def _recompute(self, _):
        self._log("Recomputing page mapping\u2026")
        self.toc_entries = compute_page_mapping(self.toc_entries, self.total_pages, 1)
        self._log("Recompute done.", "OK")
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
            self._log("Split aborted: no PDF.", "WARN")
            self.page.update()
            return

        self.progress_ring.visible = True
        self.split_status.value = "Splitting\u2026 please wait."
        self._log("Starting PDF split\u2026")
        self.page.update()

        def run():
            try:
                plan = generate_split_plan(self.toc_entries)
                self._log(f"Split plan: {len(plan)} sections.")
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
                self._log(f"Split complete: {len(files)} files \u2192 {zip_path}", "OK")
            except Exception as exc:
                self.split_status.value = f"\u274c {exc}"
                self.split_status.color = ft.Colors.RED
                self._log(f"Split error: {exc}\n{traceback.format_exc()}", "ERROR")
            self.progress_ring.visible = False
            self.page.update()

        threading.Thread(target=run, daemon=True).start()


async def main(page: ft.Page):
    PDFCutterGUI(page)


if __name__ == "__main__":
    ft.run(main)
