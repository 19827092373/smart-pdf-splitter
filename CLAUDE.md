# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Smart PDF Splitter** (智能 PDF 切分工具) - a Streamlit web application that uses multiple AI vision APIs to automatically identify table of contents from scanned PDF textbooks and split them into individual lesson PDF files.

## Architecture

### Core Components

- **`app.py`** - Main Streamlit application with three-phase workflow:
  1. Preview & Scoping: PDF upload and TOC page range identification
  2. Analysis & Review: AI-powered TOC extraction with manual editing
  3. Preview & Execute: PDF splitting with validation and ZIP download

- **`core_logic.py`** - Business logic module containing:

  **PDF Processing:**
  - `convert_pdf_to_images()` - Converts PDF pages to images using pdf2image (requires Poppler)
  - `split_pdf()` - Splits PDF based on chapter data with page offset calculation
  - `create_zip()` - Packages output files into downloadable ZIP

  **Multi-Provider Vision API:**
  - `call_vision_api(provider, ...)` - Universal router that dispatches to provider-specific handlers
  - `call_gemini_vision()` - Google Gemini API (inline_data format)
  - `call_openai_vision()` - OpenAI-compatible API (image_url format)
  - `call_claude_vision()` - Anthropic Claude API (base64 image format)
  - `call_zhipu_vision()` - Zhipu AI GLM-4V API (OpenAI-compatible)
  - `call_qwen_vision()` - Alibaba Qwen VL API (OpenAI-compatible)

  **Response Parsers:**
  - `parse_gemini_response()` - Parses `candidates[0].content.parts[0].text`
  - `parse_openai_response()` - Parses `choices[0].message.content`
  - `parse_anthropic_response()` - Parses `content[]` array with text blocks
  - `parse_zhipu_response()` - Alias to OpenAI parser
  - `parse_qwen_response()` - Alias to OpenAI parser

### Data Flow

1. User selects provider → provider config loaded (base_url, models, labels)
2. User uploads PDF → saved to temp file
3. User specifies TOC page range → images converted for preview
4. User sets offset (e.g., book page 1 = PDF page 7)
5. Vision API analyzes TOC images → returns structured JSON `[{"title": "...", "page": n}]`
6. User edits results in interactive dataframe
7. PDF split using `pypdf` with calculated page ranges
8. ZIP created and stored in session state for download

### Supported Providers

| Provider | Base URL | Vision Models | API Format |
|----------|----------|---------------|------------|
| Google Gemini | `https://generativelanguage.googleapis.com` | gemini-3-flash-preview, gemini-3-pro-preview, gemini-2.5-flash | Native |
| OpenAI | `https://api.openai.com/v1` | gpt-4.1, gpt-4o, gpt-5.2 | OpenAI-compatible |
| Anthropic Claude | `https://api.anthropic.com` | claude-3-5-sonnet, claude-3-opus, claude-3-haiku | Claude Messages API |
| 智谱 AI (Zhipu AI) | `https://open.bigmodel.cn/api/paas/v4` | glm-4.6v, glm-4.6v-flashx, glm-4v | OpenAI-compatible |
| 阿里通义千问 (Qwen) | `https://dashscope.aliyuncs.com/compatible-mode/v1` | qwen-vl-max, qwen-vl-plus, qwen2.5-vl | OpenAI-compatible |
| DeepSeek | `https://api.deepseek.com/v1` | deepseek-chat, deepseek-coder, deepseek-r1 | OpenAI-compatible |

### Key Design Patterns

- **Provider Router Pattern**: `call_vision_api()` dispatches to provider-specific handlers based on provider name
- **Session State Management**: App state (`pdf_path`, `toc_data`, `preview_images`, `zip_buffer`, `final_toc`) persists across reruns
- **Offset Calculation**: Critical formula `PDF_Page = Book_Page + Offset` handles non-standard PDF numbering
- **Bounds Validation**: Visual table shows start/end pages with error detection before splitting

## Running the Application

```bash
streamlit run app.py
```

**Prerequisites:**
- Python 3.8+
- Poppler must be installed and in PATH (Windows: download from GitHub releases, add `bin` to PATH)
- Dependencies: `streamlit pdf2image pypdf requests pandas`

## Utility Scripts

- **`check_pdf_outline.py`** - Extracts PDF outline/bookmarks using `pypdf` (for digital PDFs with embedded TOC)
- **`read_pdf_text.py`** - Dumps text from first N pages using `pypdf` (debugging tool)
- **`read_pdf_plumber.py`** - Alternative text extraction using `pdfplumber` (better layout preservation)

## Configuration

Streamlit config in `.streamlit/config.toml`:
- `headless = true` - Runs without browser auto-open
- `gatherUsageStats = false` - Disables telemetry

## API Integration

The app supports multiple vision API providers with automatic configuration:

**Provider Selection Flow:**
1. User selects provider from dropdown
2. Base URL auto-fills (can be overridden for proxies)
3. API Key label updates to match provider's format
4. Model list filters to provider's available vision models

**Adding a New Provider:**
1. Add config to `provider_config` dict in `app.py`:
   ```python
   "Provider Name": {
       "base_url": "https://api.example.com",
       "api_key_label": "Provider API Key",
       "api_key_help": "Help text",
       "models": ["model-1", "model-2"]
   }
   ```
2. Add handler to `provider_handlers` in `call_vision_api()`:
   ```python
   "Provider Name": call_provider_vision,
   ```
3. Implement `call_provider_vision(api_key, base_url, model, images, prompt)` in `core_logic.py`
4. Add parser function if response format differs from OpenAI/Gemini/Claude

**Proxy Support**: Users can override Base URL for any provider to use relay/proxy services.

## Important Constraints

- **Page Indexing**: `pdf2image` uses 1-based indexing, `pypdf` uses 0-based internally
- **Filename Sanitization**: Non-alphanumeric characters (except space, underscore, hyphen, dot) are stripped from output filenames
- **Chapter Ordering**: Chapters sorted by page number before splitting to handle out-of-order TOC entries
- **API Response Formats**: Each provider returns JSON differently - parsers handle extraction of the actual text content from provider-specific response structures
