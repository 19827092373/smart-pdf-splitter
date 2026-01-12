import sys
from pypdf import PdfReader

def get_outlines(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        outlines = reader.outline
        
        print(f"Total pages: {len(reader.pages)}")
        print("-" * 30)
        
        def recurse_outlines(outlines, level=0):
            for item in outlines:
                if isinstance(item, list):
                    recurse_outlines(item, level + 1)
                else:
                    # item.page is either a PageObject or an int index in newer versions depending on usage, 
                    # but reader.get_destination_page_number(item) is the safest way.
                    try:
                        page_num = reader.get_destination_page_number(item)
                        title = item.title
                        print(f"{'  ' * level}{title} - Page {page_num + 1}") 
                        # Try to debug encoding if it looks suspicious
                        # print(f"Raw bytes: {title.encode('latin1', errors='ignore')}") 
                    except Exception as e:
                         print(f"{'  ' * level}{item.title} - (Page unknown: {e})")

        recurse_outlines(outlines)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <pdf_file>")
    else:
        get_outlines(sys.argv[1])
