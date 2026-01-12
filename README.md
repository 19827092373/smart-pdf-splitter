# 智能 PDF 切分工具 (Smart PDF Splitter)

这是一个基于 Streamlit 和 Google Gemini Vision API 的智能 PDF 切分工具。它可以自动识别扫描版 PDF 的目录，并将每一节课切分成单独的 PDF 文件。

## 功能特点
- **可视化配置**: 在网页端直接输入 API Key、Base URL 和模型名称。
- **智能识别**: 利用 Gemini 视觉模型直接“看懂”目录图片，无需复杂的 OCR。
- **所见即所得**: 提供 PDF 预览和交互式表格，允许人工校对 AI 的识别结果。
- **一键切分**: 自动计算页码偏移，生成 ZIP 包一键下载。

## 安装与运行

### 1. 安装依赖
确保您的电脑上安装了 Python (3.8+)。然后运行：

```bash
pip install streamlit pdf2image pypdf requests pandas
```

### 2. 安装 Poppler (Windows 用户必看)
`pdf2image` 库依赖于 Poppler 工具。
- **Windows**: 下载 Poppler (例如从 [这里](https://github.com/oschwartz10612/poppler-windows/releases/)), 解压后将 `bin` 目录添加到系统的 PATH 环境变量中。
- **Mac**: `brew install poppler`
- **Linux**: `sudo apt-get install poppler-utils`

### 3. 启动应用
在终端中运行以下命令：

```bash
streamlit run app.py
```

### 4. 使用步骤
1. 打开浏览器显示的链接 (通常是 `http://localhost:8501`)。
2. 在左侧侧边栏填入您的 **Gemini API Key**。
3. 上传您的 PDF 教材。
4. 根据预览图，填写目录所在的页码范围（例如 3-5 页）。
5. 填写“页码偏移量”参考（例如：书上第1页是 PDF 的第 7 页）。
6. 点击 **"开始 AI 识别目录"**。
7. 在表格中检查识别结果，如有错误直接修改。
8. 点击 **"开始切分 PDF"** 并下载结果。

## 常见问题
- **报错 "Poppler not found"**: 请检查步骤 2，确保 Poppler 的 `bin` 路径在环境变量中。
- **API 报错**: 请检查 API Key 是否有效，或者尝试更换 Base URL (如果您在国内，可能需要代理或中转地址)。
