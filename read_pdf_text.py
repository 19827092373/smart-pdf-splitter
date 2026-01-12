from pypdf import PdfReader

def extract_text_head(pdf_path, pages=10):
    try:
        reader = PdfReader(pdf_path)
        for i in range(min(pages, len(reader.pages))):
            page = reader.pages[i]
            text = page.extract_text()
            print(f"--- Page {i+1} ---")
            print(text)
            print("\n")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    extract_text_head("25年苏科物理9下新教材.pdf")
