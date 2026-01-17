import base64
import json
import requests
import io
import zipfile
import tempfile
import os
import re
import time
import traceback
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

    # Construct URL for Google Native API
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
        response = requests.post(url, headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error_details = "No response"
        if 'response' in locals() and hasattr(response, 'text'):
            try:
                error_details = response.text
            except:
                error_details = "Unable to read response"
        return {"error": str(e), "details": error_details}

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
        "max_tokens": 8192
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error_details = "No response"
        if 'response' in locals() and hasattr(response, 'text'):
            try:
                error_details = response.text
            except:
                error_details = "Unable to read response"
        return {"error": str(e), "details": error_details}

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
        "max_tokens": 8192,
        "messages": [{"role": "user", "content": content}]
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error_details = "No response"
        if 'response' in locals() and hasattr(response, 'text'):
            try:
                error_details = response.text
            except:
                error_details = "Unable to read response"
        return {"error": str(e), "details": error_details}

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
        "max_tokens": 8192
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error_details = "No response"
        if 'response' in locals() and hasattr(response, 'text'):
            try:
                error_details = response.text
            except:
                error_details = "Unable to read response"
        return {"error": str(e), "details": error_details}

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
        "max_tokens": 8192
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=90)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        error_details = "No response"
        if 'response' in locals() and hasattr(response, 'text'):
            try:
                error_details = response.text
            except:
                error_details = "Unable to read response"
        return {"error": str(e), "details": error_details}

def parse_gemini_response(response_json):
    """
    Extract and parse JSON from Gemini response.
    """
    try:
        candidates = response_json.get('candidates', [])
        if not candidates:
            return []

        content = candidates[0].get('content', {})
        parts = content.get('parts', [])
        if not parts:
            return []

        text = parts[0].get('text', '')

        # Find JSON array
        start = text.find('[')
        end = text.rfind(']') + 1

        if start != -1 and end != -1:
            json_str = text[start:end]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as json_err:
                # Try to fix common JSON issues
                # Remove trailing commas before closing brackets/braces
                json_str_fixed = re.sub(r',\s*([}\]])', r'\1', json_str)
                try:
                    return json.loads(json_str_fixed)
                except json.JSONDecodeError:
                    print(f"Error parsing Gemini JSON: {json_err}")
                    print(f"JSON string (first 500 chars): {json_str[:500]}")
                    return []
        return []
    except Exception as e:
        print(f"Error parsing Gemini response: {e}")
        traceback.print_exc()
        return []

def parse_openai_response(response_json):
    """
    Extract and parse JSON from OpenAI-compatible response.
    """
    try:
        if 'choices' not in response_json or not response_json['choices']:
            return []

        text = response_json['choices'][0].get('message', {}).get('content', '')

        # Clean markdown code blocks
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0].strip()
        elif '```' in text:
            text = text.split('```')[1].split('```')[0].strip()

        # Find JSON array
        start = text.find('[')
        end = text.rfind(']') + 1

        if start != -1 and end != -1:
            json_str = text[start:end]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as json_err:
                # Try to fix common JSON issues
                import re
                json_str_fixed = re.sub(r',\s*([}\]])', r'\1', json_str)
                try:
                    return json.loads(json_str_fixed)
                except json.JSONDecodeError:
                    print(f"Error parsing OpenAI JSON: {json_err}")
                    print(f"JSON string (first 500 chars): {json_str[:500]}")
                    return []
        return []
    except Exception as e:
        print(f"Error parsing OpenAI response: {e}")
        traceback.print_exc()
        return []

def parse_anthropic_response(response_json):
    """
    Extract and parse JSON from Anthropic Claude response.
    """
    try:
        if 'content' not in response_json:
            return []

        content = response_json['content']
        if isinstance(content, list):
            text = ""
            for block in content:
                if block.get('type') == 'text':
                    text = block.get('text', '')
                    break
        else:
            text = str(content)

        if '```json' in text:
            text = text.split('```json')[1].split('```')[0].strip()
        elif '```' in text:
            text = text.split('```')[1].split('```')[0].strip()

        start = text.find('[')
        end = text.rfind(']') + 1

        if start != -1 and end != -1:
            json_str = text[start:end]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as json_err:
                # Try to fix common JSON issues
                import re
                json_str_fixed = re.sub(r',\s*([}\]])', r'\1', json_str)
                try:
                    return json.loads(json_str_fixed)
                except json.JSONDecodeError:
                    print(f"Error parsing Claude JSON: {json_err}")
                    print(f"JSON string (first 500 chars): {json_str[:500]}")
                    return []
        return []
    except Exception as e:
        print(f"Error parsing Claude response: {e}")
        traceback.print_exc()
        return []

def parse_zhipu_response(response_json):
    return parse_openai_response(response_json)

def parse_qwen_response(response_json):
    return parse_openai_response(response_json)

def split_pdf(original_pdf_path, chapter_data, offset, output_dir):
    """
    Split PDF based on chapter data and offset.
    - Set strict=False for pypdf to handle structural issues.
    """
    generated_files = []
    # Use strict=False to bypass structural PDF errors
    try:
        reader = PdfReader(original_pdf_path, strict=False)
        total_pages = len(reader.pages)
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return []
    
    # Sort chapters by page number
    # Assuming 'page' key exists and is the start page for the chapter
    sorted_chapters = sorted(chapter_data, key=lambda x: int(x['page']) if str(x.get('page', '')).isdigit() else 0)
    
    # Track used filenames to prevent overwrites
    used_filenames = set()
    
    for i, chapter in enumerate(sorted_chapters):
        title = chapter.get('title', f"Chapter {i+1}")
        try:
            start_page_book = int(chapter['page'])
        except (ValueError, TypeError):
            print(f"Skipping chapter {i}: Invalid start_page {chapter.get('page')}")
            continue
        
        # Convert book page number to 0-based PDF index
        start_index = start_page_book + offset - 1
        
        # Determine end page for the current chapter
        if i < len(sorted_chapters) - 1:
            # The end of the current chapter is the page before the next chapter starts
            try:
                next_start_page_book = int(sorted_chapters[i+1]['page'])
            except (ValueError, TypeError):
                # If next chapter's page is invalid, treat current chapter as extending to end of PDF
                next_start_page_book = total_pages - offset + 1 # Approximate book page for total_pages
            
            # Calculate next chapter's PDF start index (0-based)
            next_start_index = next_start_page_book + offset - 1
            # Current chapter's end index (0-based, exclusive - does not include next chapter's start page)
            end_index = next_start_index - 1
        else:
            # Last chapter goes to the end of the PDF
            end_index = total_pages
            
        # Ensure indices are within valid bounds
        start_index = max(0, start_index)
        end_index = min(total_pages, end_index)

        if start_index >= end_index:
            print(f"Skipping chapter '{title}': Start index {start_index} is not less than end index {end_index}.")
            continue
        
        writer = PdfWriter()
        pages_added = 0
        
        try:
            for page_num in range(start_index, end_index):
                if page_num >= total_pages:
                    break
                writer.add_page(reader.pages[page_num])
                pages_added += 1
        except Exception as e:
            print(f"Error adding pages for chapter '{title}': {e}")
            # Don't write this file if we couldn't add any pages
            if pages_added == 0:
                continue
            
        # Skip if no pages were added
        if pages_added == 0:
            print(f"Skipping chapter '{title}': No pages added")
            continue
            
        # Use AI-suggested filename if available, otherwise sanitize title
        if 'filename' in chapter and chapter['filename']:
            safe_title = chapter['filename']
        else:
            # Fallback: sanitize the title
            safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '_', '-', '.')]).strip()
        
        # Ensure we have a valid filename
        if not safe_title:
            safe_title = f"chapter_{i+1}"
        
        # Deduplication logic
        base_filename = safe_title
        counter = 1
        max_attempts = 1000  # Prevent infinite loop
        attempts = 0
        while f"{base_filename}.pdf" in used_filenames:
            base_filename = f"{safe_title}_{counter}"
            counter += 1
            attempts += 1
            if attempts >= max_attempts:
                # Fallback to timestamp-based filename if too many conflicts
                base_filename = f"{safe_title}_{int(time.time())}"
                break
            # Ensure base_filename is not empty
            if not base_filename:
                base_filename = f"chapter_{i+1}"
            
        filename = f"{base_filename}.pdf"
        used_filenames.add(filename)
        filepath = os.path.join(output_dir, filename)
        
        try:
            with open(filepath, "wb") as f:
                writer.write(f)
            
            # Verify file size
            file_size = os.path.getsize(filepath)
            if file_size > 0:
                generated_files.append(filepath)
                print(f"Successfully created: {filename} ({pages_added} pages, {file_size} bytes). Range: {start_index}-{end_index}")
            else:
                print(f"Error: Generated file {filename} is 0 bytes. Skipping.")
        except Exception as e:
            print(f"Error writing PDF file {filename}: {e}")
        
    return generated_files

def split_pdf_with_ranges(original_pdf_path, chapter_data, output_dir):
    """
    Split PDF using direct PDF page ranges (not book page + offset).
    chapter_data should contain '_start_pdf' and '_end_pdf' fields.
    """
    generated_files = []
    try:
        reader = PdfReader(original_pdf_path, strict=False)
        total_pages = len(reader.pages)
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return []
    
    # Sort chapters by start page
    sorted_chapters = sorted(chapter_data, key=lambda x: x.get('_start_pdf', 0))
    
    # Track used filenames to prevent overwrites
    used_filenames = set()
    
    for i, chapter in enumerate(sorted_chapters):
        title = chapter.get('title', f"Chapter {i+1}")
        
        # Get PDF page range directly
        start_pdf = chapter.get('_start_pdf', 0)
        end_pdf = chapter.get('_end_pdf', total_pages)
        
        # Convert to 0-based indices
        start_index = max(0, start_pdf - 1)
        end_index = min(total_pages, end_pdf)  # end_pdf is 1-based, end_index should be exclusive
        
        if start_index >= end_index:
            print(f"Skipping chapter '{title}': Start index {start_index} >= end index {end_index}")
            continue
        
        writer = PdfWriter()
        pages_added = 0
        
        try:
            for page_num in range(start_index, end_index):
                if page_num >= total_pages:
                    break
                writer.add_page(reader.pages[page_num])
                pages_added += 1
        except Exception as e:
            print(f"Error adding pages for chapter '{title}': {e}")
            if pages_added == 0:
                continue
        
        if pages_added == 0:
            print(f"Skipping chapter '{title}': No pages added")
            continue
        
        # Use edited filename if available
        if 'filename' in chapter and chapter['filename']:
            safe_title = chapter['filename']
            if safe_title.endswith('.pdf'):
                safe_title = safe_title[:-4]
        else:
            safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '_', '-', '.')]).strip()
            if not safe_title:
                safe_title = f"chapter_{i+1}"
        
        # Ensure we have a valid filename
        if not safe_title:
            safe_title = f"chapter_{i+1}"
        
        # Deduplication logic
        base_filename = safe_title
        counter = 1
        max_attempts = 1000
        attempts = 0
        while f"{base_filename}.pdf" in used_filenames:
            base_filename = f"{safe_title}_{counter}"
            counter += 1
            attempts += 1
            if attempts >= max_attempts:
                base_filename = f"{safe_title}_{int(time.time())}"
                break
            if not base_filename:
                base_filename = f"chapter_{i+1}"
        
        filename = f"{base_filename}.pdf"
        used_filenames.add(filename)
        filepath = os.path.join(output_dir, filename)
        
        try:
            with open(filepath, "wb") as f:
                writer.write(f)
            
            file_size = os.path.getsize(filepath)
            if file_size > 0:
                generated_files.append(filepath)
                print(f"Successfully created: {filename} ({pages_added} pages, {file_size} bytes). Range: {start_index}-{end_index}")
            else:
                print(f"Error: Generated file {filename} is 0 bytes. Skipping.")
        except Exception as e:
            print(f"Error writing PDF file {filename}: {e}")
    
    return generated_files

def create_zip(file_paths, zip_name):
    """
    Create a ZIP file from a list of file paths.
    Reads file contents into memory before adding to ZIP to avoid file deletion issues.
    Returns a BytesIO buffer containing the ZIP data.
    """
    zip_buffer = io.BytesIO()
    files_added = 0
    
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in file_paths:
            if not os.path.exists(file_path):
                print(f"Warning: File does not exist: {file_path}")
                continue
            
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                print(f"Warning: File is empty: {file_path}")
                continue
            
            try:
                # Read file content into memory before adding to ZIP
                # This ensures the file can be read even if the original file is deleted
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                
                # Add file content to ZIP using writestr (in-memory)
                zip_file.writestr(os.path.basename(file_path), file_content)
                files_added += 1
                print(f"Added to ZIP: {os.path.basename(file_path)} ({file_size} bytes)")
            except Exception as e:
                print(f"Error adding {file_path} to ZIP: {e}")
                import traceback
                traceback.print_exc()
                continue
    
    if files_added == 0:
        print("Error: No files were added to ZIP")
        return None
    
    # Reset buffer position to the beginning so it can be read
    zip_buffer.seek(0)
    
    # Validate ZIP file
    try:
        zip_buffer.seek(0)
        with zipfile.ZipFile(zip_buffer, 'r') as test_zip:
            file_list = test_zip.namelist()
            print(f"ZIP created successfully with {len(file_list)} files: {file_list}")
        zip_buffer.seek(0)
    except Exception as e:
        print(f"Error validating ZIP file: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    return zip_buffer
