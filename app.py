import streamlit as st
import os
import tempfile
import io
import zipfile
import hashlib
import pandas as pd
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
    split_pdf_with_ranges,
    create_zip
)

st.set_page_config(page_title="智能教材切分工具", layout="wide")

# ==================== Session State ====================
if 'current_step' not in st.session_state:
    st.session_state.current_step = 1
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
if 'zip_bytes' not in st.session_state:
    st.session_state.zip_bytes = None
if 'zip_file_list' not in st.session_state:
    st.session_state.zip_file_list = None
if 'zip_debug' not in st.session_state:
    st.session_state.zip_debug = None
if 'zip_path' not in st.session_state:
    st.session_state.zip_path = None
if 'zip_test_result' not in st.session_state:
    st.session_state.zip_test_result = None
if 'zip_sha256' not in st.session_state:
    st.session_state.zip_sha256 = None
if 'final_toc' not in st.session_state:
    st.session_state.final_toc = None
if 'toc_start' not in st.session_state:
    st.session_state.toc_start = 3
if 'toc_end' not in st.session_state:
    st.session_state.toc_end = 5
if 'calculated_offset' not in st.session_state:
    st.session_state.calculated_offset = 0
if 'offset_ref_book_page' not in st.session_state:
    st.session_state.offset_ref_book_page = 1
if 'offset_ref_pdf_page' not in st.session_state:
    st.session_state.offset_ref_pdf_page = 7

# 初始化API设置（从localStorage或使用默认值）
if 'selected_provider' not in st.session_state:
    st.session_state.selected_provider = 'OpenAI'
if 'api_key' not in st.session_state:
    st.session_state.api_key = ''
if 'base_url' not in st.session_state:
    st.session_state.base_url = ''
if 'model_name' not in st.session_state:
    st.session_state.model_name = 'gpt-4o'

# ==================== 从localStorage加载API设置 ====================
# 兼容新旧版本 Streamlit 的 query_params API
def get_query_params():
    """兼容新旧版本 Streamlit 获取 URL 参数"""
    try:
        # 新版本 Streamlit (>= 1.30)
        return dict(st.query_params)
    except AttributeError:
        # 旧版本 Streamlit
        try:
            params = st.experimental_get_query_params()
            # 旧版返回的是 dict of lists，转换为 dict of strings
            return {k: v[0] if v else '' for k, v in params.items()}
        except:
            return {}

def clear_query_params(keys):
    """兼容新旧版本 Streamlit 清除 URL 参数"""
    try:
        # 新版本 Streamlit (>= 1.30)
        for key in keys:
            if key in st.query_params:
                del st.query_params[key]
    except AttributeError:
        # 旧版本 Streamlit
        try:
            current = st.experimental_get_query_params()
            for key in keys:
                current.pop(key, None)
            st.experimental_set_query_params(**current)
        except:
            pass

# 使用JavaScript在页面加载时读取localStorage并设置到session_state
if 'api_settings_loaded' not in st.session_state:
    # 注入JavaScript来读取localStorage并通过URL参数传递
    load_settings_js = """
    <script>
    (function() {
        setTimeout(function() {
            try {
                const saved = localStorage.getItem('pdf_splitter_api_settings');
                if (saved) {
                    const settings = JSON.parse(saved);
                    const url = new URL(window.location);
                    if (!url.searchParams.has('loaded_settings')) {
                        url.searchParams.set('loaded_settings', '1');
                        if (settings.provider) url.searchParams.set('provider', settings.provider);
                        if (settings.api_key) url.searchParams.set('api_key', settings.api_key);
                        if (settings.base_url) url.searchParams.set('base_url', settings.base_url);
                        if (settings.model) url.searchParams.set('model', settings.model);
                        window.location.href = url.toString();
                    }
                }
            } catch(e) {
                console.error('Error loading settings:', e);
            }
        }, 100);
    })();
    </script>
    """
    st.components.v1.html(load_settings_js, height=0)
    
    # 从URL参数读取设置（如果存在）
    query_params = get_query_params()
    if query_params.get('loaded_settings') == '1':
        if 'provider' in query_params:
            st.session_state.selected_provider = query_params.get('provider', 'OpenAI')
        if 'api_key' in query_params:
            st.session_state.api_key = query_params.get('api_key', '')
        if 'base_url' in query_params:
            st.session_state.base_url = query_params.get('base_url', '')
        if 'model' in query_params:
            st.session_state.model_name = query_params.get('model', 'gpt-4o')
        # 清除URL参数（避免URL过长）
        clear_query_params(['loaded_settings', 'provider', 'api_key', 'base_url', 'model'])
    
    st.session_state.api_settings_loaded = True

# ==================== 步骤定义 ====================
STEPS = {
    1: "上传PDF",
    2: "预览定位",
    3: "AI识别",
    4: "切分下载"
}

# ==================== 辅助函数 ====================
def is_step_enabled(step_num):
    if step_num == 1: return True
    if step_num == 2: return st.session_state.get('pdf_path') is not None
    if step_num == 3: return len(st.session_state.get('preview_images', [])) > 0
    if step_num == 4: return len(st.session_state.get('toc_data', [])) > 0
    return False

def is_step_completed(step_num):
    if step_num == 1: return st.session_state.get('pdf_path') is not None
    if step_num == 2: return len(st.session_state.get('preview_images', [])) > 0
    if step_num == 3: return len(st.session_state.get('toc_data', [])) > 0
    if step_num == 4: return st.session_state.get('zip_bytes') is not None
    return False

# ==================== 步骤导航 ====================
def render_step_navigation():
    cols = st.columns(4)
    
    for i, (step_num, step_name) in enumerate(STEPS.items()):
        with cols[i]:
            is_current = step_num == st.session_state.current_step
            is_enabled = is_step_enabled(step_num)
            is_completed = is_step_completed(step_num)

            # Determine button type and label
            if is_current:
                icon = "●"
                button_type = "primary"
            elif is_completed:
                icon = "✓"
                button_type = "secondary"
            elif is_enabled:
                icon = ""
                button_type = "secondary"
            else:
                icon = "🔒"
                button_type = "secondary"

            # Create button label
            label = f"{icon} 步骤{step_num}: {step_name}" if icon else f"步骤{step_num}: {step_name}"
            
            # Render as button (disabled for current/locked, clickable for others)
            if is_current:
                st.button(label, type=button_type, disabled=True, key=f"nav_current_{step_num}")
            elif is_enabled:
                if st.button(label, type=button_type, key=f"nav_{step_num}"):
                    st.session_state.current_step = step_num
                    st.rerun()
            else:
                st.button(label, type=button_type, disabled=True, key=f"nav_disabled_{step_num}")

def render_navigation_buttons():
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if st.session_state.current_step > 1:
            if st.button("← 上一步"):
                st.session_state.current_step -= 1
                st.rerun()

    with col3:
        next_step = st.session_state.current_step + 1
        if next_step <= 4 and is_step_enabled(next_step):
            if st.button("下一步 →", type="primary"):
                st.session_state.current_step = next_step
                st.rerun()

# ==================== 步骤1：上传PDF ====================
def render_step_1():
    st.subheader("📄 上传PDF文件")
    
    uploaded_file = st.file_uploader(
        "请上传需要切分的 PDF 教材文件",
        type=["pdf"],
        help="支持扫描版和数字版 PDF，最大 200MB"
    )

    if uploaded_file:
        if st.session_state.current_filename != uploaded_file.name:
            # Clean up old temporary file if exists
            old_pdf_path = st.session_state.get('pdf_path')
            if old_pdf_path and os.path.exists(old_pdf_path):
                try:
                    os.unlink(old_pdf_path)
                except Exception as e:
                    print(f"Warning: Could not delete old temp file {old_pdf_path}: {e}")
            
            # Save new file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                st.session_state.pdf_path = tmp_file.name
            st.session_state.current_filename = uploaded_file.name
            st.session_state.toc_data = []
            st.session_state.preview_images = []
            st.session_state.zip_buffer = None
            st.session_state.zip_bytes = None
            st.session_state.zip_file_list = None
            st.session_state.zip_debug = None
            st.session_state.zip_path = None
            st.session_state.zip_test_result = None
            st.session_state.zip_sha256 = None
            st.session_state.final_toc = None

        st.success(f"✓ 已上传：{uploaded_file.name}")
        st.toast("📄 文件上传成功!", icon="✅")
        st.info("点击「下一步」继续")

# ==================== 步骤2：预览定位 ====================
def render_step_2():
    st.subheader("🔍 预览定位")
    
    col1, col2 = st.columns([1, 2])

    with col1:
        st.info("请查看右侧预览图，确定目录所在的页码范围。")
        # IMPORTANT: Do NOT use 'key' for conditionally rendered widgets!
        # Streamlit clears key-bound values when the widget is not rendered.
        # Use manual session state assignment instead.
        toc_start = st.number_input(
            "目录起始页", 
            min_value=1, 
            value=st.session_state.toc_start, 
            help="PDF页码"
        )
        st.session_state.toc_start = toc_start
        
        toc_end = st.number_input(
            "目录结束页", 
            min_value=1, 
            value=st.session_state.toc_end, 
            help="PDF页码"
        )
        st.session_state.toc_end = toc_end

        st.markdown("---")
        st.subheader("📏 页码偏移设置")
        st.caption("用于将书本页码转换为PDF页码")
        
        offset_ref_book_page = st.number_input(
            "参考：正文第1课在书上的页码", 
            min_value=1, 
            value=st.session_state.offset_ref_book_page,
            help="通常是 1"
        )
        st.session_state.offset_ref_book_page = offset_ref_book_page
        
        offset_ref_pdf_page = st.number_input(
            "对应 PDF 的实际页码", 
            min_value=1, 
            value=st.session_state.offset_ref_pdf_page,
            help="请看右侧预览图确认"
        )
        st.session_state.offset_ref_pdf_page = offset_ref_pdf_page
        
        # Calculate offset
        calculated_offset = offset_ref_pdf_page - offset_ref_book_page
        st.session_state.calculated_offset = calculated_offset
        
        st.success(f"✓ 页码偏移量: **{calculated_offset}**")
        st.caption(f"公式: PDF页码 = 书本页码 + {calculated_offset}")

        if st.button("生成预览图"):
            # State is already updated via keys

            with st.spinner("正在生成预览..."):
                images = convert_pdf_to_images(st.session_state.pdf_path, 1, 10)
                st.session_state.preview_images = images
            st.rerun()

    with col2:
        if st.session_state.preview_images:
            st.write("**PDF 前 10 页预览:**")
            # First row: pages 1-5
            row1_cols = st.columns(5)
            for i in range(min(5, len(st.session_state.preview_images))):
                with row1_cols[i]:
                    img = st.session_state.preview_images[i]
                    st.image(img, caption=f"Page {i+1}")
                    with st.expander(f"🔍 放大"):
                        st.image(img)

            # Second row: pages 6-10
            if len(st.session_state.preview_images) > 5:
                row2_cols = st.columns(5)
                for i in range(5, min(10, len(st.session_state.preview_images))):
                    with row2_cols[i-5]:
                        img = st.session_state.preview_images[i]
                        st.image(img, caption=f"Page {i+1}")
                        with st.expander(f"🔍 放大"):
                            st.image(img)
        else:
            st.info("点击左侧「生成预览图」按钮查看 PDF 页面")

# ==================== 步骤3：AI识别 ====================
def render_step_3():
    st.subheader("🤖 AI识别")
    
    # Show configuration summary
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**当前配置:**")
        provider = st.session_state.get('selected_provider', 'OpenAI')
        model = st.session_state.get('model_name', 'gpt-4o')
        st.write(f"• 模型提供商: {provider}")
        st.write(f"• 模型: {model}")
    
    with col2:
        st.markdown("**目录范围:**")
        st.write(f"• 目录页码: {st.session_state.toc_start} - {st.session_state.toc_end}")
        st.write(f"• 页码偏移量: {st.session_state.calculated_offset}")
    
    st.markdown("---")

    api_key = st.session_state.get('api_key', '')
    if not api_key:
        st.error("请先在侧边栏配置 API Key")
    else:
        if st.button("🚀 开始 AI 识别", type="primary"):
                progress_container = st.empty()
                progress_container.info("🔄 正在将目录页面发送至 AI...")
                
                with st.spinner("正在分析目录..."):
                    toc_images = convert_pdf_to_images(st.session_state.pdf_path, st.session_state.toc_start, st.session_state.toc_end)
                    
                    progress_container.info("🧠 AI 正在分析目录结构...")

                    prompt = st.session_state.ai_prompt

                    selected_provider = st.session_state.get('selected_provider', 'OpenAI')
                    base_url = st.session_state.get('base_url', 'https://api.openai.com/v1')
                    model_name = st.session_state.get('model_name', 'gpt-4o')

                    response = call_vision_api(selected_provider, api_key, base_url, model_name, toc_images, prompt)

                    if "error" in response:
                        st.error(f"API Error: {response['error']}")
                    else:
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
                            parsed_data = parse_openai_response(response)

                        if parsed_data:
                            st.session_state.toc_data = parsed_data
                            progress_container.success("✅ 分析完成!")
                            st.success(f"成功识别 {len(parsed_data)} 个章节！")
                            st.toast(f"🤖 成功识别 {len(parsed_data)} 个章节!", icon="✅")
                            st.rerun()
                        else:
                            st.error("未能解析出有效的 JSON 数据。")

    # 默认提示词（存储在 session state 中，允许用户编辑）
    if 'ai_prompt' not in st.session_state:
        default_prompt = """# Role
你是一位精通教材结构分析与数据清洗的AI助手。你的核心任务是识别教材目录图片的视觉层级，并将其转换为标准化的、可用于程序自动切分PDF的JSON数据。

# Context
用户将提供一张或多张教材目录的图片。这可能是语文、数学、物理、化学、生物、地理、政治、历史、英语等任何学科的教材。你需要提取每一项独立的教学内容（包括课题、单元导读、综合实践活动、实验、习题等）。

# Goals
1. **精准识别**：识别出目录中的所有条目，包括章节号、标题、起始页码。
2. **类型分类**：区分"课题"、"导读"、"实验"、"习题"、"附录"等不同类型。
3. **标准化命名**：生成一个清洗后的文件名建议。

# Workflow (思维链)
在输出最终JSON前，请先进行以下逻辑判断：
1. **分析层级**：通过缩进、字体大小判断，哪个是"章"（一级），哪个是"节"（二级）。
2. **识别章节大标题页**（重要！）：
   - **章节大标题页的特征**：通常单独占一页，显示章节号和大标题（如"第一章 声现象"、"Chapter 1"、"第十五章 XX"），字体较大、居中显示
   - **关键规则**：章节大标题页的页码应该作为**新章节的起始页码**，而不是上一章节的结束页码
   - **示例**：如果目录显示"第一章 声现象 ... 1"，"1.1 声音的产生与传播 ... 4"，那么：
     * 正确：第一章起始页 = 1（大标题页），1.1节起始页 = 4
     * 错误：不要将第1页（大标题页）归入上一章节
   - **特别注意**：如果目录中显示章节大标题有明确的页码（如"第一章 声现象 ... 1"、"第十五章 XX ... 120"），**必须**将该页码识别为新章节的起始页
3. **识别内容类型**：
   - **章节大标题页**：章节大标题单独占一页（如"第一章 XX"、"第十五章 XX"、"Chapter 1"），通常页码较小，应该单独识别为一个条目，类型标记为"导读"或"课题"
   - **课题**：教材的主要教学内容（如"1.1 声音的产生与传播"、"第1节 XX"、"Lesson 1"）
   - **导读**：章节开头的导语、引言、概述页面（非大标题页）
   - **实验**：实验、探究活动、综合实践等动手类内容
   - **习题**：练习题、复习题、思考题等
   - **附录**：参考资料、索引、答案等
4. **生成文件名**：格式为 `{序号}_{类型标签}_{标题}`，去除特殊字符。

# Constraints & Rules
- **章节大标题页处理规则**（非常重要！）：
  - 如果目录中显示章节号+大标题有明确的页码（如"第一章 声现象 ... 1"、"第十五章 XX ... 120"），**必须**将该页码识别为新章节的起始页
  - 章节大标题页（单独一页）**不能**归入上一章节，必须作为新章节的开始
  - 如果章节大标题页和第一个小节在同一页，则以该页作为章节起始页
- **页码识别规则**：
  - 优先使用目录中明确标注的页码
  - 如果章节大标题有页码，使用该页码；如果没有，使用第一个小节的页码减1（假设大标题页在前）
- **忽略无效行**：只忽略纯装饰性的文字或完全没有页码信息的标题行。
- **命名规范**：
  - 序号：保持目录的原始序号（如 "1.1", "第一章", "Ch01"），如果没有序号则用递增数字。
  - 类型标签：课题、导读、习题、实验、活动、附录
  - 标题：保持原标题，去除特殊字符
- **输出格式**：**只输出标准的 JSON 数组**，不要包含 markdown 代码块标记（```json），不要包含任何解释性文字。

# Output Format (JSON)
每个条目必须包含以下字段：
- title: 原始标题（必需，用于显示和切分）
- page: 起始页码（必需，整数）
- type: 内容类型（可选，值为：课题/导读/实验/习题/附录）
- filename: 建议的文件名（可选，不含.pdf后缀）

# Example Output
[
  {
    "title": "第一章 声现象",
    "page": 1,
    "type": "导读",
    "filename": "Ch01_导读_声现象"
  },
  {
    "title": "1.1 声音的产生与传播",
    "page": 4,
    "type": "课题",
    "filename": "1.1_课题_声音的产生与传播"
  },
  {
    "title": "1.2 声音的特性",
    "page": 9,
    "type": "课题",
    "filename": "1.2_课题_声音的特性"
  },
  {
    "title": "第二章 光现象",
    "page": 20,
    "type": "导读",
    "filename": "Ch02_导读_光现象"
  },
  {
    "title": "2.1 光的传播",
    "page": 23,
    "type": "课题",
    "filename": "2.1_课题_光的传播"
  },
  {
    "title": "综合实践活动：自制乐器",
    "page": 25,
    "type": "实验",
    "filename": "活动_自制乐器"
  }
]

# 重要说明
- 注意示例中"第一章 声现象"的起始页是1（大标题页），"第二章 光现象"的起始页是20（大标题页）
- 每个章节的大标题页都应该单独识别，页码作为该章节的起始页
- 不要将章节大标题页归入上一章节

# Task
现在，请根据上传的目录图片，严格按照上述逻辑和格式输出 JSON 数据。
特别注意：如果目录中显示章节大标题有明确的页码，必须将该页码识别为新章节的起始页，不要将其归入上一章节。"""
        st.session_state.ai_prompt = default_prompt
    
    # 显示和编辑提示词
    with st.expander("📝 查看/编辑 AI 识别提示词", expanded=False):
        st.markdown("**提示词说明**：您可以修改下方的提示词来优化AI的识别效果。修改后点击「开始 AI 识别」按钮将使用新的提示词。")
        edited_prompt = st.text_area(
            "AI 识别提示词",
            value=st.session_state.ai_prompt,
            height=400,
            help="修改提示词可以优化AI识别效果，特别是针对章节大标题页的识别",
            key="prompt_editor"
        )
        st.session_state.ai_prompt = edited_prompt
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🔄 重置为默认提示词"):
                st.session_state.ai_prompt = default_prompt
                st.rerun()
        with col_b:
            st.info(f"提示词长度: {len(st.session_state.ai_prompt)} 字符")

    # 数据编辑
    if st.session_state.toc_data:
        st.info("请在下方表格中校对识别结果。")
        df = pd.DataFrame(st.session_state.toc_data)
        
        # Ensure 'page' column is integer type
        if 'page' in df.columns:
            df['page'] = pd.to_numeric(df['page'], errors='coerce').fillna(0).astype(int)
            df['pdf_start_page'] = df['page'] + st.session_state.calculated_offset

        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            width='stretch',
            column_config={
                "title": "章节标题",
                "page": st.column_config.NumberColumn("书本页码", min_value=1, step=1),
                "pdf_start_page": st.column_config.NumberColumn("PDF起始页", disabled=True)
            }
        )
        
        # Convert back to dict, ensuring page is int
        final_toc = edited_df.to_dict('records')
        for item in final_toc:
            if 'page' in item:
                try:
                    item['page'] = int(item['page'])
                except (ValueError, TypeError):
                    item['page'] = 0
        st.session_state.final_toc = final_toc


# ==================== 步骤4：切分下载 ====================
def render_step_4():
    st.subheader("✂️ 切分下载")

    try:
        reader = PdfReader(st.session_state.pdf_path, strict=False)
        total_pdf_pages = len(reader.pages)
        st.info(f"PDF 总页数: **{total_pdf_pages}**")
    except Exception as e:
        st.error(f"无法读取 PDF: {e}")
        return

    if not st.session_state.final_toc:
        st.warning("没有章节数据，请先完成 AI 识别。")
        return

    # ========== 预处理：验证所有章节（不分离，只标记错误）==========
    offset = st.session_state.calculated_offset
    
    # Sort by page number
    sorted_chapters = sorted(
        st.session_state.final_toc, 
        key=lambda x: int(x.get('page', 0)) if str(x.get('page', '')).isdigit() else 0
    )
    
    # 处理所有章节，计算页码范围并标记错误
    all_chapters_with_validation = []
    
    for i, chapter in enumerate(sorted_chapters):
        title = chapter.get('title', f'Chapter {i+1}')
        error_reason = None
        
        # Parse start page
        try:
            start_book = int(chapter.get('page', 0))
        except (ValueError, TypeError):
            error_reason = '页码无效（非数字）'
            all_chapters_with_validation.append({
                **chapter,
                '_start_pdf': 0,
                '_end_pdf': 0,
                '_error': error_reason,
                '_is_valid': False
            })
            continue
            
        if start_book <= 0:
            error_reason = '页码无效（<= 0）'
            all_chapters_with_validation.append({
                **chapter,
                '_start_pdf': 0,
                '_end_pdf': 0,
                '_error': error_reason,
                '_is_valid': False
            })
            continue
            
        start_pdf = start_book + offset
        
        # Calculate end page (1-based)
        if i < len(sorted_chapters) - 1:
            try:
                next_start_book = int(sorted_chapters[i+1].get('page', 0))
            except (ValueError, TypeError):
                next_start_book = start_book
            # Next chapter's PDF start page (1-based)
            next_start_pdf = next_start_book + offset
            # Current chapter's end page (1-based, exclusive - does not include next chapter's start page)
            end_pdf = next_start_pdf - 1
        else:
            end_pdf = total_pdf_pages
        
        # Validation checks
        if start_pdf > total_pdf_pages:
            error_reason = f'起始页 {start_pdf} 超出 PDF 范围 (最大 {total_pdf_pages})'
            all_chapters_with_validation.append({
                **chapter,
                '_start_pdf': start_pdf,
                '_end_pdf': end_pdf,
                '_error': error_reason,
                '_is_valid': False
            })
            continue
        if start_pdf > end_pdf:
            error_reason = f'起始页 {start_pdf} > 结束页 {end_pdf}'
            all_chapters_with_validation.append({
                **chapter,
                '_start_pdf': start_pdf,
                '_end_pdf': end_pdf,
                '_error': error_reason,
                '_is_valid': False
            })
            continue
        if start_pdf < 1:
            error_reason = f'起始页 {start_pdf} < 1'
            all_chapters_with_validation.append({
                **chapter,
                '_start_pdf': start_pdf,
                '_end_pdf': end_pdf,
                '_error': error_reason,
                '_is_valid': False
            })
            continue
            
        # Valid chapter
        all_chapters_with_validation.append({
            **chapter,
            '_start_pdf': start_pdf,
            '_end_pdf': end_pdf,
            '_error': None,
            '_is_valid': True
        })
    
    # 统计有效和无效章节
    valid_count = sum(1 for ch in all_chapters_with_validation if ch.get('_is_valid', False))
    invalid_count = len(all_chapters_with_validation) - valid_count
    
    # 显示统计信息
    if invalid_count > 0:
        st.warning(f"⚠️ 发现 {invalid_count} 个无效章节（红色标记），请编辑修复后继续")
    if valid_count > 0:
        st.success(f"✅ {valid_count} 个有效章节可以切分")
    else:
        st.error("❌ 没有有效的章节可以切分！请编辑下方表格修复错误。")
    
    # 显示可编辑的章节预览表格（包含所有章节，包括错误的）
    st.markdown("### 📋 编辑切分设置")
    st.info("💡 您可以在下方表格中编辑所有章节的文件名和页码范围。错误章节会用红色标记，修复后会自动变为有效。")
    
    # 准备编辑数据（使用 session state 存储编辑后的数据）
    # 使用固定的 key，避免动态 key 导致的问题
    editor_key = "chapter_editor_all"
    
    # 检查是否需要初始化数据（章节数量变化或首次加载）
    chapters_hash = hash(tuple((ch.get('title', ''), ch.get('page', 0)) for ch in all_chapters_with_validation))
    if 'all_chapters_hash' not in st.session_state or st.session_state.all_chapters_hash != chapters_hash:
        # 初始化编辑数据
        edited_data = []
        for idx, ch in enumerate(all_chapters_with_validation, 1):
            title = ch.get('title', f'章节{idx}')
            filename = ch.get('filename', '')
            if not filename:
                safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '_', '-', '.')]).strip()
                if not safe_title:
                    safe_title = f"chapter_{idx}"
                filename = f"{safe_title}.pdf"
            else:
                if not filename.endswith('.pdf'):
                    filename = f"{filename}.pdf"
                else:
                    # 移除 .pdf 后缀以便编辑
                    filename = filename[:-4]
            
            edited_data.append({
                "序号": idx,
                "状态": "❌ 错误" if not ch.get('_is_valid', False) else "✅ 有效",
                "章节标题": title,
                "文件名": filename,  # 不带 .pdf 后缀，方便编辑
                "PDF起始页": ch['_start_pdf'],
                "PDF结束页": ch['_end_pdf'],
                "页数": ch['_end_pdf'] - ch['_start_pdf'] + 1 if ch['_start_pdf'] > 0 and ch['_end_pdf'] > 0 else 0,
                "错误信息": ch.get('_error', '') if not ch.get('_is_valid', False) else ''
            })
        st.session_state.all_chapters_data = edited_data
        st.session_state.all_chapters_hash = chapters_hash
    
    # 确保 all_chapters_data 存在
    if 'all_chapters_data' not in st.session_state:
        st.session_state.all_chapters_data = []
    
    # 显示可编辑表格（包含所有章节）
    df_editable = pd.DataFrame(st.session_state.all_chapters_data)
    
    st.info("💡 提示：您可以点击行号左侧的垃圾桶图标 🗑️ 删除不需要的章节行")
    
    edited_df = st.data_editor(
        df_editable,
        num_rows="dynamic",  # 允许添加和删除行
        hide_index=True,
        column_config={
            "序号": st.column_config.NumberColumn("序号", width="small", disabled=True),
            "状态": st.column_config.TextColumn("状态", width="small", disabled=True),
            "章节标题": st.column_config.TextColumn("章节标题", width="large", disabled=True),
            "文件名": st.column_config.TextColumn("文件名", width="medium", help="编辑文件名（不含.pdf后缀）"),
            "PDF起始页": st.column_config.NumberColumn("起始页", min_value=1, max_value=total_pdf_pages, step=1, width="small", help="PDF页码"),
            "PDF结束页": st.column_config.NumberColumn("结束页", min_value=1, max_value=total_pdf_pages, step=1, width="small", help="PDF页码"),
            "页数": st.column_config.NumberColumn("页数", width="small", disabled=True),
            "错误信息": st.column_config.TextColumn("错误信息", width="medium", disabled=True),
        },
        key=editor_key
    )
    
    # 更新页数列（基于编辑后的起始页和结束页）
    edited_df['页数'] = edited_df['PDF结束页'] - edited_df['PDF起始页'] + 1
    
    # 重新验证编辑后的数据
    edited_chapters_validated = []
    validation_errors = []
    
    for idx, row in edited_df.iterrows():
        start_pdf = int(row['PDF起始页'])
        end_pdf = int(row['PDF结束页'])
        filename = str(row['文件名']).strip()
        title = str(row['章节标题'])
        
        # 验证
        is_valid = True
        error_reason = None
        
        if start_pdf > end_pdf:
            is_valid = False
            error_reason = f'起始页 {start_pdf} > 结束页 {end_pdf}'
        elif start_pdf < 1 or start_pdf > total_pdf_pages:
            is_valid = False
            error_reason = f'起始页 {start_pdf} 超出范围 (1-{total_pdf_pages})'
        elif end_pdf < 1 or end_pdf > total_pdf_pages:
            is_valid = False
            error_reason = f'结束页 {end_pdf} 超出范围 (1-{total_pdf_pages})'
        elif not filename:
            is_valid = False
            error_reason = '文件名不能为空'
        
        # 更新状态
        edited_df.at[idx, '状态'] = "✅ 有效" if is_valid else "❌ 错误"
        edited_df.at[idx, '错误信息'] = error_reason if not is_valid else ''
        
        # 构建章节数据
        # 使用序号找到原始章节（序号从1开始，索引从0开始）
        row_num = int(row['序号'])
        if row_num <= len(all_chapters_with_validation):
            original_ch = all_chapters_with_validation[row_num - 1]
        else:
            # 如果是新添加的行（虽然不应该发生，但为了安全），创建一个新的章节数据
            original_ch = {
                'title': title,
                'page': start_pdf - offset if start_pdf >= offset else 0,
                'filename': '',
                'type': ''
            }
        
        if not filename.endswith('.pdf'):
            filename = f"{filename}.pdf"
        
        chapter_data = {
            **original_ch,
            'filename': filename,
            '_start_pdf': start_pdf,
            '_end_pdf': end_pdf,
            '_is_valid': is_valid,
            '_error': error_reason
        }
        
        edited_chapters_validated.append(chapter_data)
        
        if not is_valid:
            validation_errors.append(f"第 {row_num} 行「{title}」: {error_reason}")
    
    # 更新显示
    updated_valid_count = sum(1 for ch in edited_chapters_validated if ch.get('_is_valid', False))
    updated_invalid_count = len(edited_chapters_validated) - updated_valid_count
    
    # 显示验证结果
    if updated_invalid_count > 0:
        st.warning(f"⚠️ 仍有 {updated_invalid_count} 个无效章节需要修复")
        with st.expander("查看错误详情", expanded=False):
            for error in validation_errors:
                st.text(f"  • {error}")
    else:
        st.success(f"✅ 所有章节验证通过！共 {updated_valid_count} 个有效章节")
    
    # 保存编辑后的数据（只保存到 all_chapters_data，不直接设置 widget 的值）
    # 更新序号列，确保序号连续
    edited_df['序号'] = range(1, len(edited_df) + 1)
    st.session_state.all_chapters_data = edited_df.to_dict('records')
    
    # 更新 hash，以便下次检测到变化
    if len(edited_df) != len(all_chapters_with_validation):
        # 如果行数变化了，更新 hash 以便下次重新初始化
        st.session_state.all_chapters_hash = hash(tuple((ch.get('title', ''), ch.get('_start_pdf', 0)) for ch in edited_chapters_validated))
    
    # 提取有效章节用于切分
    edited_valid_chapters = [ch for ch in edited_chapters_validated if ch.get('_is_valid', False)]
    
    # ========== 切分按钮 ==========
    if updated_invalid_count > 0:
        st.warning("⚠️ 请先修复所有错误章节后再进行切分")
    
    if st.button("开始切分 PDF", type="primary", disabled=updated_invalid_count > 0 or len(edited_valid_chapters) == 0):
        with st.spinner("正在切分..."):
            with tempfile.TemporaryDirectory() as temp_out_dir:
                # 使用编辑后的章节数据，直接使用 PDF 页码范围进行切分
                files = split_pdf_with_ranges(
                    st.session_state.pdf_path,
                    edited_valid_chapters,
                    temp_out_dir
                )

                if files:
                    # Verify all files exist before creating ZIP
                    existing_files = [f for f in files if os.path.exists(f)]
                    missing_files = [f for f in files if not os.path.exists(f)]
                    
                    if missing_files:
                        st.warning(f"⚠️ {len(missing_files)} 个文件在创建ZIP前已丢失")
                        for mf in missing_files:
                            st.text(f"  - {os.path.basename(mf)}")
                    
                    if not existing_files:
                        st.error("❌ 所有文件都已丢失，无法创建ZIP！")
                    else:
                        original_name = os.path.splitext(st.session_state.current_filename)[0]
                        zip_name = f"{original_name}_split.zip"
                        
                        # Create ZIP buffer BEFORE temp directory is deleted
                        zip_buffer = create_zip(existing_files, zip_name)
                        
                        if zip_buffer is None:
                            st.error("❌ ZIP文件创建失败！请检查控制台日志。")
                        else:
                            zip_bytes = zip_buffer.getvalue()
                            zip_size = len(zip_bytes)
                            if zip_size == 0:
                                st.error("生成的 ZIP 文件为空！")
                            else:
                                # Validate ZIP bytes
                                signature_ok = zip_bytes[:4] in (b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08')
                                is_zip = zipfile.is_zipfile(io.BytesIO(zip_bytes))
                                if not signature_ok or not is_zip:
                                    st.error("❌ ZIP 文件校验失败：文件格式不正确。")
                                    st.text(f"ZIP 大小: {zip_size} bytes, 头部: {zip_bytes[:4]}")
                                else:
                                    # Store ZIP bytes in session state (avoid BytesIO issues on rerun)
                                    st.session_state.zip_bytes = zip_bytes
                                    st.session_state.zip_buffer = None
                                    st.session_state.zip_file_list = [os.path.basename(f) for f in existing_files]
                                    st.session_state.zip_debug = {
                                        "size": zip_size,
                                        "header": zip_bytes[:4],
                                        "file_count": len(existing_files),
                                    }
                                    
                                    # Persist ZIP to disk for troubleshooting
                                    try:
                                        tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
                                        tmp_zip.write(zip_bytes)
                                        tmp_zip.flush()
                                        tmp_zip.close()
                                        st.session_state.zip_path = tmp_zip.name
                                    except Exception as e:
                                        st.session_state.zip_path = None
                                        print(f"Error saving ZIP to disk: {e}")
                                    
                                    # Compute ZIP checksum and test integrity
                                    try:
                                        st.session_state.zip_sha256 = hashlib.sha256(zip_bytes).hexdigest()
                                        with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
                                            bad_file = zf.testzip()
                                        st.session_state.zip_test_result = bad_file  # None means OK
                                    except Exception as e:
                                        st.session_state.zip_test_result = f"ERROR: {e}"
                                    
                                    # Show file list
                                    st.success(f"✅ 切分成功！共生成 {len(existing_files)} 个文件，ZIP 大小: {zip_size / 1024:.2f} KB")
                                    
                                    # Display file list
                                    with st.expander("📁 查看生成的文件列表", expanded=True):
                                        file_list_data = [{"序号": i+1, "文件名": name} for i, name in enumerate(st.session_state.zip_file_list)]
                                        st.dataframe(pd.DataFrame(file_list_data), hide_index=True)
                                    
                                    # Display ZIP debug info (collapsed)
                                    with st.expander("🔍 ZIP 校验信息", expanded=False):
                                        st.text(f"ZIP 大小: {zip_size} bytes")
                                        st.text(f"ZIP 头部: {zip_bytes[:4]}")
                                        try:
                                            with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
                                                st.text(f"ZIP 文件数: {len(zf.namelist())}")
                                                st.text(f"文件列表: {', '.join(zf.namelist()[:10])}")
                                        except Exception as e:
                                            st.text(f"ZIP 读取失败: {e}")
                                    
                                    st.toast("✂️ PDF 切分完成!", icon="✅")
                    # Do not rerun here to avoid clearing the file list display
                else:
                    st.warning("没有生成任何文件")

    # 下载按钮
    if st.session_state.zip_bytes:
        st.markdown("---")
        original_name = os.path.splitext(st.session_state.current_filename)[0]
        download_name = f"{original_name}_split.zip"

        st.download_button(
            label="下载切分好的文件包 (ZIP)",
            data=st.session_state.zip_bytes,
            file_name=download_name,
            mime="application/zip"
        )
        
        if st.session_state.zip_file_list:
            with st.expander("📁 最近生成的文件列表", expanded=False):
                file_list_data = [{"序号": i+1, "文件名": name} for i, name in enumerate(st.session_state.zip_file_list)]
                st.dataframe(pd.DataFrame(file_list_data), use_container_width=True, hide_index=True)
        
        if st.session_state.zip_debug:
            with st.expander("🔍 最近 ZIP 校验信息", expanded=False):
                st.text(f"ZIP 大小: {st.session_state.zip_debug.get('size')} bytes")
                st.text(f"ZIP 头部: {st.session_state.zip_debug.get('header')}")
                if st.session_state.zip_sha256:
                    st.text(f"SHA256: {st.session_state.zip_sha256}")
                if st.session_state.zip_test_result is None:
                    st.text("ZIP 完整性: OK (testzip 无错误)")
                else:
                    st.text(f"ZIP 完整性: {st.session_state.zip_test_result}")
                if st.session_state.zip_path:
                    st.text(f"ZIP 磁盘路径: {st.session_state.zip_path}")


# ==================== 侧边栏 ====================
with st.sidebar:
    st.markdown("### ⚙️ 设置")
    
    # 1. 当前状态 (放在最上面)
    st.markdown("---")
    st.markdown("### 📊 当前状态")
    
    # 文件信息
    if st.session_state.get('current_filename'):
        st.markdown(f"**📄 文件**: {st.session_state.current_filename}")
        if st.session_state.get('pdf_path'):
            try:
                reader = PdfReader(st.session_state.pdf_path, strict=False)
                st.markdown(f"**📑 页数**: {len(reader.pages)}")
            except:
                pass
    else:
        st.info("尚未上传文件")

    # 识别进度
    toc_count = len(st.session_state.get('toc_data', []))
    if toc_count > 0:
        st.markdown(f"**📚 已识别章节**: {toc_count} 个")

    # 当前步骤
    current = st.session_state.get('current_step', 1)
    st.markdown(f"**🚀 当前步骤**: {current}. {STEPS.get(current, '')}")
    
    # 2. API 设置
    st.markdown("---")
    with st.expander("🔑 API 连接设置", expanded=False):
        provider_config = {
            "OpenAI": {
                "base_url": "https://api.openai.com/v1",
                "api_key_label": "OpenAI API Key",
                "api_key_help": "输入您的 OpenAI API Key (sk-...)",
                "models": [
                    "gpt-5.2", 
                    "gpt-5.2-thinking", 
                    "gpt-5.2-pro", 
                    "gpt-5.2-chat-latest",
                    "gpt-5.2-codex",
                    "gpt-5.1", 
                    "gpt-5.1-chat-latest",
                    "gpt-5", 
                    "gpt-5-mini",
                    "gpt-5-nano",
                    "o4-mini",
                    "o3-pro",
                    "o3-mini",
                    "o3",
                    "o1-pro",
                    "o1",
                    "o1-mini",
                    "gpt-4.1",
                    "gpt-4o"
                ]
            },
            "Google Gemini": {
                "base_url": "https://generativelanguage.googleapis.com",
                "api_key_label": "Gemini API Key",
                "api_key_help": "输入您的 Google Gemini API Key",
                "models": [
                    "gemini-3-pro-preview", 
                    "gemini-3-flash-preview", 
                    "gemini-3-deep-think",
                    "gemini-2.5-pro", 
                    "gemini-2.5-flash", 
                    "gemini-2.0-flash"
                ]
            },
            "Anthropic Claude": {
                "base_url": "https://api.anthropic.com",
                "api_key_label": "Claude API Key",
                "api_key_help": "输入您的 Anthropic API Key (sk-ant-...)",
                "models": [
                    "claude-sonnet-4-5",
                    "claude-opus-4-5",
                    "claude-4-5-sonnet-20260101", 
                    "claude-4-5-opus-20260101", 
                    "claude-4-5-haiku-20260101",
                    "claude-3-5-sonnet-latest"
                ]
            },
            "智谱 AI (Zhipu AI)": {
                "base_url": "https://open.bigmodel.cn/api/paas/v4",
                "api_key_label": "智谱 API Key",
                "api_key_help": "输入您的智谱 API Key",
                "models": [
                    "glm-4v-plus-0111", 
                    "glm-4v-plus", 
                    "glm-4v", 
                    "glm-z1-air",
                    "glm-4-plus"
                ]
            },
            "阿里通义千问 (Qwen)": {
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "api_key_label": "Qwen API Key",
                "api_key_help": "输入您的阿里云 API Key (sk-...)",
                "models": [
                    "qwen3-vl-plus",
                    "qwen3-max",
                    "qwen-vl-max-2026", 
                    "qwen-vl-plus-2026", 
                    "qwen-vl-max-latest"
                ]
            },
            "DeepSeek": {
                "base_url": "https://api.deepseek.com/v1",
                "api_key_label": "DeepSeek API Key",
                "api_key_help": "输入您的 DeepSeek API Key (sk-...)",
                "models": [
                    "deepseek-chat", 
                    "deepseek-reasoner"
                ]
            }
        }

        provider_names = list(provider_config.keys())
        
        # 获取保存的设置值（优先使用session_state中的值）
        default_provider = st.session_state.get('selected_provider', 'OpenAI')
        if default_provider not in provider_names:
            default_provider = 'OpenAI'
        
        selected_provider = st.selectbox(
            "模型提供商", 
            options=provider_names,
            index=provider_names.index(default_provider),
            key="provider_select"
        )
        st.session_state.selected_provider = selected_provider

        config = provider_config[selected_provider]
        
        # 获取保存的设置值
        saved_api_key = st.session_state.get('api_key', '')
        saved_base_url = st.session_state.get('base_url', config["base_url"])
        saved_model = st.session_state.get('model_name', config["models"][0])
        if saved_model not in config["models"]:
            saved_model = config["models"][0]
        
        api_key = st.text_input(
            config["api_key_label"], 
            value=saved_api_key,
            type="password", 
            help=config["api_key_help"],
            key="api_key_input"
        )
        st.session_state.api_key = api_key

        base_url = st.text_input(
            "Base URL", 
            value=saved_base_url,
            key="base_url_input"
        )
        st.session_state.base_url = base_url

        model_index = config["models"].index(saved_model) if saved_model in config["models"] else 0
        model_name = st.selectbox(
            "模型", 
            options=config["models"],
            index=model_index,
            key="model_select"
        )
        st.session_state.model_name = model_name
        
        # 自动保存设置到localStorage（每次设置改变时）
        save_settings_js = f"""
        <script>
        (function() {{
            try {{
                const settings = {{
                    provider: {repr(selected_provider)},
                    api_key: {repr(api_key)},
                    base_url: {repr(base_url)},
                    model: {repr(model_name)}
                }};
                localStorage.setItem('pdf_splitter_api_settings', JSON.stringify(settings));
            }} catch(e) {{
                console.error('Error saving settings:', e);
            }}
        }})();
        </script>
        """
        st.components.v1.html(save_settings_js, height=0)
        
        # 隐私声明和清除按钮
        st.markdown("---")
        st.caption("🔒 **隐私说明**：以上设置仅保存在您的浏览器本地缓存中，不会上传到任何服务器。您可以随时清除浏览器缓存来删除这些设置。")
        
        col_clear1, col_clear2 = st.columns(2)
        with col_clear1:
            if st.button("🗑️ 清除保存的设置", help="清除浏览器本地保存的API设置"):
                clear_settings_js = """
                <script>
                (function() {
                    try {
                        localStorage.removeItem('pdf_splitter_api_settings');
                        alert('设置已清除！页面将刷新。');
                        window.location.reload();
                    } catch(e) {
                        console.error('Error clearing settings:', e);
                    }
                })();
                </script>
                """
                st.components.v1.html(clear_settings_js, height=0)
                # 清除session_state中的设置
                st.session_state.api_key = ''
                st.session_state.base_url = ''
                st.session_state.model_name = config["models"][0]
                st.rerun()

        # 在 api_key 输入后添加测试按钮
        if api_key:
            # Add some spacing
            st.markdown("")
            if st.button("🔌 测试连接"):
                with st.spinner("正在测试..."):
                    from core_logic import call_vision_api
                    # Use a very small text-only challenge for the vision API (some support text-only, others need image)
                    # To be safe, we'll create a 1x1 black pixel image to verify vision capability
                    try:
                        from PIL import Image
                        import io
                        img = Image.new('RGB', (10, 10), color='black')
                        
                        test_prompt = "Reply with 'OK' if you can see this."
                        
                        # Call the actual vision function
                        response = call_vision_api(
                            selected_provider, 
                            api_key, 
                            base_url, 
                            model_name, 
                            [img], 
                            test_prompt
                        )
                        
                        if "error" in response:
                            st.error(f"连接失败: {response['error']}")
                        else:
                            st.success("✓ 连接成功! API 响应正常。")
                            
                    except ImportError:
                         st.error("Missing PIL (Pillow) library for test image generation.")
                    except Exception as e:
                        st.error(f"测试异常: {str(e)}")

# ==================== 主界面 ====================
st.markdown("""
<div style="text-align: center; padding: 1.5rem 0; border-bottom: 1px solid #e5e7eb; margin-bottom: 1.5rem;">
    <h1 style="margin: 0; font-size: 1.75rem; color: #171717;">智能教材切分工具</h1>
    <p style="margin: 0.5rem 0 0 0; color: #6B7280; font-size: 0.9rem;">
        AI 驱动的 PDF 目录识别与自动切分
    </p>
</div>
""", unsafe_allow_html=True)

# 步骤导航
render_step_navigation()

st.markdown("---")

# 当前步骤内容
step = st.session_state.current_step
st.markdown(f"### 步骤 {step}：{STEPS[step]}")

if step == 1:
    render_step_1()
elif step == 2:
    render_step_2()
elif step == 3:
    render_step_3()
elif step == 4:
    render_step_4()

# 底部导航按钮
st.markdown("---")
render_navigation_buttons()
