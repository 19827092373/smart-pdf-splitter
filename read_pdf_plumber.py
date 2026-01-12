import pdfplumber

def extract_text_plumber(pdf_path, pages=10):
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i in range(min(pages, len(pdf.pages))):
                page = pdf.pages[i]
                text = page.extract_text()
                print(f"--- Page {i+1} ---")
                if text:
                    print(text)
                else:
                    print("(No text found)")
                print("\n")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    extract_text_plumber("25年苏科物理9下新教材.pdf")
