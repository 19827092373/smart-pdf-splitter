import streamlit as st
import os
import tempfile
import pandas as pd
import shutil
from pypdf import PdfReader
from core_logic import (
    convert_pdf_to_images,
    call_vision_api,
    parse_gemini_response,
    parse_openai_response,
    parse_anthropic_response,
    parse_qwen_response,
    parse_zhipu_response,
    split_pdf,
    create_zip
)

st.set_page_config(page_title="智能 PDF 切分工具 (Smart PDF Splitter)", layout="wide")

# Session State Initialization
if 'pdf_path' not in st.session_state:
    st.session_state.pdf_path = None
if 'current_filename' not in st.session_state:
    st.session_state.current_filename = None
if 'toc_data' not in st.session_state:
    st.session_state.toc_data = []
if 'preview_images' not in st.session_state:
    st.session_state.preview_images = []
if 'zip_buffer' not in st.session_state:
    st.session_state.zip_buffer = None

# Sidebar Configuration
with st.sidebar:
    # API Configuration in Expander for cleaner UI
    with st.expander("🔌 API 连接设置 (Connection Settings)", expanded=True):
        # Provider Selection
        provider_config = {
            "Google Gemini": {
                "base_url": "https://generativelanguage.googleapis.com",
                "api_key_label": "Gemini API Key",
                "api_key_help": "输入您的 Google Gemini API Key",
                "models": [
                    "gemini-3-flash-preview",
                    "gemini-3-pro-preview",
                    "gemini-3-pro-image-preview",
                    "gemini-2.5-flash",
                    "gemini-2.5-flash-lite",
                    "gemini-2.5-pro",
                    "gemini-2.0-flash-exp",
                    "gemini-2.0-flash",
                    "gemini-1.5-pro",
                    "gemini-1.5-flash"
                ]
            },
            "OpenAI": {
                "base_url": "https://api.openai.com/v1",
                "api_key_label": "OpenAI API Key",
                "api_key_help": "输入您的 OpenAI API Key (sk-...)",
                "models": [
                    "gpt-4.1",
                    "gpt-4.1-mini",
                    "gpt-4o",
                    "gpt-4o-mini",
                    "gpt-5.2",
                    "gpt-5-mini"
                ]
            },
            "Anthropic Claude": {
                "base_url": "https://api.anthropic.com",
                "api_key_label": "Claude API Key",
                "api_key_help": "输入您的 Anthropic API Key (sk-ant-...)",
                "models": [
                    "claude-3-5-sonnet-20241022",
                    "claude-3-5-haiku-20241022",
                    "claude-3-opus-20240229",
                    "claude-3-sonnet-20240229",
                    "claude-3-haiku-20240307"
                ]
            },
            "智谱 AI (Zhipu AI)": {
                "base_url": "https://open.bigmodel.cn/api/paas/v4",
                "api_key_label": "智谱 API Key",
                "api_key_help": "输入您的智谱 API Key",
                "models": [
                    "glm-4.6v",
                    "glm-4.6v-flashx",
                    "glm-4.6v-flash",
                    "glm-4v",
                    "glm-4v-plus"
                ]
            },
            "阿里通义千问 (Qwen)": {
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "api_key_label": "DashScope API Key",
                "api_key_help": "输入您的阿里云 DashScope API Key (sk-...)",
                "models": [
                    "qwen-vl-max",
                    "qwen-vl-plus",
                    "qwen-vl-v1",
                    "qwen2.5-vl-72b-instruct"
                ]
            },
            "DeepSeek": {
                "base_url": "https://api.deepseek.com/v1",
                "api_key_label": "DeepSeek API Key",
                "api_key_help": "输入您的 DeepSeek API Key (sk-...)",
                "models": [
                    "deepseek-chat",
                    "deepseek-coder",
                    "deepseek-r1"
                ]
            }
        }

        provider_names = list(provider_config.keys())
        selected_provider = st.selectbox("模型提供商 (Provider)", options=provider_names, index=0)

        # Get config for selected provider
        config = provider_config[selected_provider]
        default_base_url = config["base_url"]

        api_key = st.text_input(
            config["api_key_label"],
            type="password",
            help=config["api_key_help"]
        )
        base_url = st.text_input(
            "Base URL",
            value=default_base_url,
            help="API 基础地址 (如果使用中转服务请修改此处)"
        )

        # Provider-specific warnings
        if selected_provider == "Google Gemini" and api_key and api_key.startswith("sk-") and "googleapis.com" in base_url:
            st.warning("⚠️ 检测到 'sk-' 开头的 Key，请务必将 Base URL 修改为服务商提供的地址！")

        # Model Selection based on provider
        model_options = config["models"]
        selected_model = st.selectbox(
            "模型选择 (Model)",
            options=model_options + ["自定义..."],
            index=0
        )

        if selected_model == "自定义...":
            if selected_provider == "Google Gemini":
                default_custom = "gemini-2.5-flash"
            elif selected_provider == "OpenAI":
                default_custom = "gpt-4o"
            elif selected_provider == "Anthropic Claude":
                default_custom = "claude-3-5-sonnet-20241022"
            elif selected_provider == "智谱 AI (Zhipu AI)":
                default_custom = "glm-4.6v"
            elif selected_provider == "阿里通义千问 (Qwen)":
                default_custom = "qwen-vl-plus"
            else:
                default_custom = "custom-model"
            model_name = st.text_input("输入自定义模型名称", value=default_custom)
        else:
            model_name = selected_model
    
    st.markdown("---")
    st.markdown("**使用说明:**")
    st.markdown("1. 上传扫描版 PDF")
    st.markdown("2. 查看预览，确认目录页范围")
    st.markdown("3. 设置正文偏移量")
    st.markdown("4. AI 识别目录")
    st.markdown("5. 校对并切分下载")

# Step 1: File Upload
uploaded_file = st.file_uploader("上传 PDF 文件 (Upload PDF)", type=["pdf"])

if uploaded_file:
    # Check if file has changed using the original filename
    if st.session_state.current_filename != uploaded_file.name:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            st.session_state.pdf_path = tmp_file.name
        
        st.session_state.current_filename = uploaded_file.name
        st.success(f"文件已上传: {uploaded_file.name}")
        
        # Clear previous state ONLY when file changes
        st.session_state.toc_data = []
        st.session_state.preview_images = []
        st.session_state.zip_buffer = None
        st.session_state.final_toc = None # Clear toc data as well

    # Preview Section
    st.subheader("1. 预览与定位 (Preview & Scoping)")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.info("请查看右侧预览图，确定目录所在的页码范围。")
        toc_start = st.number_input("目录起始页 (PDF页码)", min_value=1, value=3)
        toc_end = st.number_input("目录结束页 (PDF页码)", min_value=1, value=5)
        
        preview_btn = st.button("生成预览图 (Generate Preview)")
        
    with col2:
        if preview_btn and st.session_state.pdf_path:
            with st.spinner("正在生成预览..."):
                # Preview a range covering likely TOC and start of content
                images = convert_pdf_to_images(st.session_state.pdf_path, 1, 10)
                st.session_state.preview_images = images
        
        if st.session_state.preview_images:
            st.write("PDF 前 10 页预览:")
            img_cols = st.columns(5)
            for i, img in enumerate(st.session_state.preview_images):
                with img_cols[i % 5]:
                    st.image(img, caption=f"Page {i+1}", width='stretch')

    st.markdown("---")

    # Step 2: Offset Configuration & AI Analysis
    st.subheader("2. AI 识别与校对 (Analysis & Review)")
    
    col_input, col_action = st.columns([2, 1])
    
    with col_input:
        offset_ref_book_page = st.number_input("参考：正文第 1 课在书上的页码 (通常是 1)", value=1)
        offset_ref_pdf_page = st.number_input("对应 PDF 的实际页码 (请看预览图)", value=7)
        
        # Calculate offset: PDF_Page = Book_Page + Offset
        # Offset = PDF_Page - Book_Page
        calculated_offset = offset_ref_pdf_page - offset_ref_book_page
        st.caption(f"当前计算的页码偏移量 (Offset): **{calculated_offset}** (PDF页码 = 书本页码 + {calculated_offset})")

    with col_action:
        st.write("") # Spacer
        st.write("") 
        analyze_btn = st.button("🤖 开始 AI 识别目录", type="primary")

    if analyze_btn:
        if not api_key:
            st.error("请先在左侧侧边栏输入 API Key")
        else:
            with st.spinner(f"正在请求 {selected_provider} API 分析目录... (这可能需要十几秒)"):
                toc_images = convert_pdf_to_images(st.session_state.pdf_path, toc_start, toc_end)

                prompt = """
You are a sophisticated document structure parser specializing in Table of Contents (TOC) extraction.

### GOAL
Extract a structured list of lessons/sections from the provided images for the purpose of splitting a PDF book.

### CORE REASONING & EXTRACTION RULES
1. **Hierarchical Context (CRITICAL)**:
   - You must scan the text linearly.
   - Always track the **Current Chapter** (e.g., "第十五章", "Chapter 1", "Unit 3").
   - When you encounter a **Section/Lesson** (e.g., "一、电能", "Section 1", "1.1"), you MUST combine it with the **Current Chapter** info to create a unique title.

2. **Naming Convention (Unique & Descriptive)**:
   - **Standard Format**: `[Chapter Number/ID].[Section Number/ID] [Title]`
   - **Example**:
     - If Chapter is "第十五章" (15) and Section is "一、电能" (1), Output Title: **"15.1 电能"**
     - If Chapter is "Unit 1" and Section is "Reading", Output Title: **"Unit 1 - Reading"**
   - **Fallback**: If there is no clear chapter number, use the Section Title as is.

3. **Constraint - Uniqueness**:
   - Ensure every generated title is unique. If two sections have the exact same name, append the page number or parent chapter to distinguish them.

4. **Target Content**:
   - Extract ONLY entries that point to a specific starting page number.
   - Ignore structural placeholders that do not correspond to actual content pages (unless they are the content itself).

### OUTPUT FORMAT
Return ONLY a raw JSON array of objects. No markdown formatting.
[
    {"title": "15.1 电能", "page": 2},
    {"title": "15.2 电功率", "page": 6},
    {"title": "附录 词汇表", "page": 105}
]
"""

                response = call_vision_api(selected_provider, api_key, base_url, model_name, toc_images, prompt)

                if "error" in response:
                    st.error(f"API Error: {response['error']}")
                    st.json(response)
                else:
                    # Parse response based on provider
                    if selected_provider == "Google Gemini":
                        parsed_data = parse_gemini_response(response)
                    elif selected_provider == "OpenAI":
                        parsed_data = parse_openai_response(response)
                    elif selected_provider == "Anthropic Claude":
                        parsed_data = parse_anthropic_response(response)
                    elif selected_provider == "智谱 AI (Zhipu AI)":
                        parsed_data = parse_zhipu_response(response)
                    elif selected_provider == "阿里通义千问 (Qwen)":
                        parsed_data = parse_qwen_response(response)
                    else:
                        # Default to OpenAI format for DeepSeek and others
                        parsed_data = parse_openai_response(response)

                    if parsed_data:
                        st.session_state.toc_data = parsed_data
                        st.success(f"成功识别 {len(parsed_data)} 个章节！")
                    else:
                        st.error("未能解析出有效的 JSON 数据。请重试或检查 API 响应。")
                        st.json(response)

    # Data Editor
    if st.session_state.toc_data:
        st.info("请在下方表格中校对识别结果。您可以直接修改标题、页码，或添加/删除行。")
        
        # Convert to DataFrame for editing
        df = pd.DataFrame(st.session_state.toc_data)
        
        # Add calculated columns for reference
        if 'page' in df.columns:
            df['pdf_start_page'] = df['page'] + calculated_offset
        
        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            width='stretch',
            column_config={
                "title": "章节标题",
                "page": "书本页码",
                "pdf_start_page": "PDF起始页 (预览)"
            }
        )
        
        st.session_state.final_toc = edited_df.to_dict('records')

        st.markdown("---")
        
        # Step 3: Split Preview & Execution
        st.subheader("3. 切分预览与执行 (Preview & Execute)")
        
        # Get PDF info for validation
        try:
            reader = PdfReader(st.session_state.pdf_path)
            total_pdf_pages = len(reader.pages)
            st.info(f"📄 当前 PDF 总页数: **{total_pdf_pages}**")
        except Exception as e:
            st.error("无法读取 PDF 页数，文件可能损坏。")
            total_pdf_pages = 0

        # Generate Split Plan Preview
        preview_data = []
        is_valid_plan = True
        
        if st.session_state.final_toc:
            sorted_chapters = sorted(st.session_state.final_toc, key=lambda x: int(x['page']) if str(x['page']).isdigit() else 0)
            
            for i, chapter in enumerate(sorted_chapters):
                try:
                    start_book = int(chapter['page'])
                except:
                    start_book = 0
                    
                # Calculate PDF Page Index (1-based for display)
                start_pdf = start_book + calculated_offset
                
                # Determine End Page
                if i < len(sorted_chapters) - 1:
                    try:
                        end_book = int(sorted_chapters[i+1]['page'])
                    except:
                        end_book = start_book
                    end_pdf = end_book + calculated_offset - 1
                else:
                    end_pdf = total_pdf_pages
                
                status = "✅ 正常"
                if start_pdf > total_pdf_pages:
                    status = "❌ 超出范围 (起始页 > 总页数)"
                    is_valid_plan = False
                elif start_pdf > end_pdf:
                     status = "⚠️ 范围错误 (起始 > 结束)"
                     # This might happen if chapters are out of order
                
                preview_data.append({
                    "章节标题": chapter['title'],
                    "PDF 起始页": start_pdf,
                    "PDF 结束页": end_pdf,
                    "状态": status
                })
            
            st.table(pd.DataFrame(preview_data))

            if not is_valid_plan:
                st.error("❌ 检测到页码超出范围！请回到上面的 '2. AI 识别与校对' 区域，减小 'PDF 实际页码' 的数值，或者检查表格中的页码是否正确。")
            else:
                if st.button("✂️ 开始切分 PDF", type="primary"):
                    with st.spinner("正在切分 PDF..."):
                        with tempfile.TemporaryDirectory() as temp_out_dir:
                            files = split_pdf(
                                st.session_state.pdf_path, 
                                st.session_state.final_toc, 
                                calculated_offset, 
                                temp_out_dir
                            )
                            
                            if files:
                                # Create ZIP and store in session state
                                zip_buffer = create_zip(files, "split_files.zip")
                                st.session_state.zip_buffer = zip_buffer
                                st.success(f"✅ 切分成功！共生成 {len(files)} 个文件。请点击下方按钮下载。")
                            else:
                                st.warning("没有生成任何文件，请检查页码范围是否超出了 PDF 总页数。")
                
                # Show Download Button if buffer exists
                if st.session_state.zip_buffer:
                    st.download_button(
                        label="⬇️ 点击下载切分好的文件包 (ZIP)",
                        data=st.session_state.zip_buffer.getvalue(),
                        file_name="split_pdf_files.zip",
                        mime="application/zip",
                        width='stretch'
                    )
else:
    st.info("👋 请先上传一个 PDF 文件开始。")
