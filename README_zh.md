# pdfcutter

[English](README.md) | [简体中文](README_zh.md) | [Français (Canada)](README_fr_CA.md)

一个用于根据目录 (TOC) 分割扫描版语言学习 PDF 的本地桌面应用程序。

`pdfcutter` 使用先进的 OCR（在线/离线）技术来读取 PDF 页面中的目录，自动提取章节标题和页码，然后将原始 PDF 切割成多个独立的章节文件。

## 功能特性
- **灵活的识别模式：**
  - **在线 OCR (LlamaParse)：** 使用 LlamaIndex 的 LlamaCloud 代理级别解析，精准提取复杂表格和排版。
  - **离线 OCR (Docling)：** 本地运行，高精度文档转换及布局分析。无需 API 密钥。
- **自动提取：** 从 OCR 结果中提取文本，并将其解析为可编辑的结构化表格格式。
- **预览与编辑：** 在结构化表格中查看提取的目录。纠正错误、添加或删除条目，并让程序重新计算实际的 PDF 页面映射。
- **分割与下载：** 为每个章节生成独立的 PDF 文件，并将其打包为 ZIP 压缩包下载。
- **原生桌面 GUI：** 使用 Flet 构建，提供流畅的桌面使用体验。

## 前置条件

- **Python 3.10+**
- **Poppler：** 用于 `pymupdf` 和 `pdf2image` 的图像提取。
- **LlamaParse API Key (可选)：** 如果你想使用在线识别模式。可以在 [LlamaCloud](https://cloud.llamaindex.ai) 获取免费密钥。

## 安装步骤

1. 克隆仓库：
    ```bash
    git clone https://github.com/etspower/pdfcutter.git
    cd pdfcutter
    ```

2. 安装依赖：
    ```bash
    pip install -r requirements.txt
    ```
    *注意：安装用于离线 OCR 的 `docling` 在首次运行时会下载约 500MB 的模型。*

3. 设置环境变量：
    ```bash
    cp .env.example .env
    ```
    编辑 `.env` 文件，填入你的 `LLAMAPARSE_API_KEY`。

## 运行程序

运行桌面应用程序：
```bash
python gui.py
```

## 工作原理

1. **步骤 1: 配置与上传：** 选择 PDF 并指定目录页码范围。选择 **在线 (LlamaParse)** 或 **离线 (Docling)** 识别模式。
2. **步骤 2: 预览与运行：** 预览目录页面并点击 **Run OCR Extraction**。程序将从图像中提取文本并将其转化为可编辑列表。
3. **步骤 3: 审核与编辑：** 程序根据识别到的第一个阿拉伯数字页码计算偏移量。你可以在此处手动调整标题、层级或 PDF 起始页。
4. **步骤 4: 执行分割：** 确认分割方案后点击 **Split PDF & Save**。

## 架构设计
- **GUI (`gui.py`)**: 基于 Flet 的桌面界面。
- **OCR 客户端 (`src/ocr_client.py`, `src/docling_client.py`)**: 集成 LlamaParse (在线) 和 Docling (离线)。
- **PDF 工具 (`src/pdf_utils.py`)**: 使用 `PyMuPDF` 和 `pypdf` 进行 PDF 渲染和分割。
- **逻辑模块 (`src/toc_extract.py`, `src/split_logic.py`)**: 数据验证和页面偏移量计算。

## 致谢
本项目深受以下优秀开源项目的启发与支持：
- [Docling](https://docling-project.github.io/docling/) - 提供强大的本地 OCR 和文档转换能力。
- [LlamaParse](https://github.com/run-llama/llama_parse) - 提供行业领先的在线文档解析和提取服务。
- [Flet](https://flet.dev/) - 助力使用 Python 构建精美的桌面应用程序。
- [PyMuPDF](https://pymupdf.readthedocs.io/) & [pypdf](https://pypdf.readthedocs.io/) - 用于 PDF 处理和渲染。

## 许可证
MIT
