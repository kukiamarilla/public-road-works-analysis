import sys
import json
from pathlib import Path

# Add src directory to Python path to allow imports
src_dir = Path(__file__).parent.parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from modules.pdf_reader import PDFReader

def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <pdf_file_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    try:
        pdf_reader = PDFReader(pdf_path)
        markdown = pdf_reader.read_pdf_as_markdown()
        
        # Pretty print the JSON output
        print(markdown)
        
    except Exception as e:
        print(f"Error processing PDF: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()