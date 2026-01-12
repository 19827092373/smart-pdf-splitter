import base64
import json
import requests
import io
import zipfile
import tempfile
import os
from pypdf import PdfReader, PdfWriter
from pdf2image import convert_from_path

def convert_pdf_to_images(pdf_path, first_page, last_page):
    """
    Convert specific pages of a PDF to images using pdf2image.
    """
    try:
        # pdf2image uses 1-based indexing for first_page and last_page
        images = convert_from_path(pdf_path, first_page=first_page, last_page=last_page)
        return images
    except Exception as e:
        print(f"Error converting PDF to images: {e}")
        return []

def encode_image(image):
    """
    Convert PIL Image to base64 string.
    """
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def call_gemini_vision(api_key, base_url, model, images, prompt):
    """
    Call Gemini Vision API.
    """
    # Clean base_url
    base_url = base_url.rstrip('/')
    if not base_url.startswith('http'):
        base_url = f"https://{base_url}"
        
    # Construct URL for Google Native API
    url = f"{base_url}/v1beta/models/{model}:generateContent?key={api_key}"
    
    # Debug print
    print(f"Request URL: {url}")
    
    headers = {
        "Content-Type": "application/json"
    }
    
    parts = [{"text": prompt}]
    
    for img in images:
        b64_data = encode_image(img)
        parts.append({
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": b64_data
            }
        })
        
    payload = {
        "contents": [
            {
                "parts": parts
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "details": response.text if 'response' in locals() else "No response"}

def call_vision_api(provider, api_key, base_url, model, images, prompt):
    """
    Universal Vision API caller supporting multiple providers.
    """
    provider_handlers = {
        "Google Gemini": call_gemini_vision,
        "OpenAI": call_openai_vision,
        "Anthropic Claude": call_claude_vision,
        "智谱 AI (Zhipu AI)": call_zhipu_vision,
        "阿里通义千问 (Qwen)": call_qwen_vision,
        "DeepSeek": call_openai_vision,  # DeepSeek uses OpenAI-compatible API
    }

    handler = provider_handlers.get(provider, call_openai_vision)
    return handler(api_key, base_url, model, images, prompt)


def call_gemini_vision(api_key, base_url, model, images, prompt):
    """
    Call Gemini Vision API.
    """
    base_url = base_url.rstrip('/')
    if not base_url.startswith('http'):
        base_url = f"https://{base_url}"

    url = f"{base_url}/v1beta/models/{model}:generateContent?key={api_key}"

    print(f"Gemini Request URL: {url}")

    headers = {"Content-Type": "application/json"}

    parts = [{"text": prompt}]
    for img in images:
        b64_data = encode_image(img)
        parts.append({
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": b64_data
            }
        })

    payload = {"contents": [{"parts": parts}]}

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "details": response.text if 'response' in locals() else "No response"}


def call_openai_vision(api_key, base_url, model, images, prompt):
    """
    Call OpenAI-compatible Vision API (OpenAI, DeepSeek, etc.).
    """
    base_url = base_url.rstrip('/')
    if not base_url.startswith('http'):
        base_url = f"https://{base_url}"

    url = f"{base_url}/chat/completions"

    print(f"OpenAI Request URL: {url}")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    # Build content with images
    content = [{"type": "text", "text": prompt}]
    for img in images:
        b64_data = encode_image(img)
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{b64_data}"
            }
        })

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 4096
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "details": response.text if 'response' in locals() else "No response"}


def call_claude_vision(api_key, base_url, model, images, prompt):
    """
    Call Anthropic Claude Vision API.
    """
    base_url = base_url.rstrip('/')
    if not base_url.startswith('http'):
        base_url = f"https://{base_url}"

    url = f"{base_url}/v1/messages"

    print(f"Claude Request URL: {url}")

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }

    # Build content with images
    content = [{"type": "text", "text": prompt}]
    for img in images:
        b64_data = encode_image(img)
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": b64_data
            }
        })

    payload = {
        "model": model,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": content}]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "details": response.text if 'response' in locals() else "No response"}


def call_zhipu_vision(api_key, base_url, model, images, prompt):
    """
    Call Zhipu AI Vision API (GLM-4V).
    Uses OpenAI-compatible format.
    """
    base_url = base_url.rstrip('/')
    if not base_url.startswith('http'):
        base_url = f"https://{base_url}"

    url = f"{base_url}/chat/completions"

    print(f"Zhipu Request URL: {url}")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    # Build content with images
    content = [{"type": "text", "text": prompt}]
    for img in images:
        b64_data = encode_image(img)
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{b64_data}"
            }
        })

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 4096
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "details": response.text if 'response' in locals() else "No response"}


def call_qwen_vision(api_key, base_url, model, images, prompt):
    """
    Call Qwen Vision API (Alibaba DashScope).
    Uses OpenAI-compatible format.
    """
    base_url = base_url.rstrip('/')
    if not base_url.startswith('http'):
        base_url = f"https://{base_url}"

    url = f"{base_url}/chat/completions"

    print(f"Qwen Request URL: {url}")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    # Build content with images
    content = [{"type": "text", "text": prompt}]
    for img in images:
        b64_data = encode_image(img)
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{b64_data}"
            }
        })

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 4096
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e), "details": response.text if 'response' in locals() else "No response"}


def parse_gemini_response(response_json):
    """
    Extract and parse JSON from Gemini response.
    """
    try:
        candidates = response_json.get('candidates', [])
        if not candidates:
            return []

        text = candidates[0].get('content', {}).get('parts', [])[0].get('text', '')

        # Simple cleanup to find JSON array
        start = text.find('[')
        end = text.rfind(']') + 1

        if start != -1 and end != -1:
            json_str = text[start:end]
            return json.loads(json_str)
        return []
    except Exception as e:
        print(f"Error parsing Gemini response: {e}")
        return []


def parse_openai_response(response_json):
    """
    Extract and parse JSON from OpenAI-compatible response.
    """
    try:
        # OpenAI format: choices[0].message.content
        if 'choices' not in response_json or not response_json['choices']:
            return []

        text = response_json['choices'][0].get('message', {}).get('content', '')

        # Clean markdown code blocks if present
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0].strip()
        elif '```' in text:
            text = text.split('```')[1].split('```')[0].strip()

        # Find JSON array
        start = text.find('[')
        end = text.rfind(']') + 1

        if start != -1 and end != -1:
            json_str = text[start:end]
            return json.loads(json_str)
        return []
    except Exception as e:
        print(f"Error parsing OpenAI response: {e}")
        return []


def parse_anthropic_response(response_json):
    """
    Extract and parse JSON from Anthropic Claude response.
    """
    try:
        # Claude format: content[0].text (if text block) or content array with text type
        if 'content' not in response_json:
            return []

        content = response_json['content']

        # Handle both block format and array format
        if isinstance(content, list):
            # Find the first text block
            text = ""
            for block in content:
                if block.get('type') == 'text':
                    text = block.get('text', '')
                    break
        else:
            text = str(content)

        # Clean markdown code blocks if present
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0].strip()
        elif '```' in text:
            text = text.split('```')[1].split('```')[0].strip()

        # Find JSON array
        start = text.find('[')
        end = text.rfind(']') + 1

        if start != -1 and end != -1:
            json_str = text[start:end]
            return json.loads(json_str)
        return []
    except Exception as e:
        print(f"Error parsing Claude response: {e}")
        return []


def parse_zhipu_response(response_json):
    """
    Extract and parse JSON from Zhipu AI response (OpenAI-compatible).
    """
    # Zhipu uses OpenAI-compatible format
    return parse_openai_response(response_json)


def parse_qwen_response(response_json):
    """
    Extract and parse JSON from Qwen response (OpenAI-compatible).
    """
    # Qwen uses OpenAI-compatible format
    return parse_openai_response(response_json)

def split_pdf(original_pdf_path, chapter_data, offset, output_dir):
    """
    Split PDF based on chapter data and offset.
    Returns list of generated file paths.
    """
    generated_files = []
    reader = PdfReader(original_pdf_path)
    total_pages = len(reader.pages)
    
    # Sort by page number to ensure correct processing
    sorted_chapters = sorted(chapter_data, key=lambda x: x['page'])
    
    # Track used filenames to prevent overwrites
    used_filenames = set()
    
    for i, chapter in enumerate(sorted_chapters):
        title = chapter['title']
        start_page_book = int(chapter['page'])
        
        # Calculate PDF page indices (0-based)
        start_index = start_page_book + offset - 1
        
        # Determine end index
        if i < len(sorted_chapters) - 1:
            next_start_page_book = int(sorted_chapters[i+1]['page'])
            end_index = next_start_page_book + offset - 1
        else:
            # Last chapter goes to the end of the file
            end_index = total_pages
            
        # Bounds check
        if start_index >= total_pages:
            continue
        
        writer = PdfWriter()
        for page_num in range(start_index, min(end_index, total_pages)):
            writer.add_page(reader.pages[page_num])
            
        # Sanitize filename - keep Chinese characters, digits, spaces, and basic punctuation
        # Allow alphanumeric, underscore, hyphen, dot, space, and non-ascii (e.g. Chinese)
        safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '_', '-', '.')]).strip()
        
        # Deduplication logic
        base_filename = safe_title
        counter = 1
        while f"{base_filename}.pdf" in used_filenames:
            base_filename = f"{safe_title}_{counter}"
            counter += 1
            
        filename = f"{base_filename}.pdf"
        used_filenames.add(filename)
        
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, "wb") as f:
            writer.write(f)
            
        generated_files.append(filepath)
        
    return generated_files

def create_zip(file_paths, zip_name):
    """
    Create a zip file from a list of files.
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in file_paths:
            zip_file.write(file_path, os.path.basename(file_path))
    
    return zip_buffer
