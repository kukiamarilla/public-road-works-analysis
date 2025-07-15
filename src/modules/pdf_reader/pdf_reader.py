import pdfplumber
import camelot
import os
import tempfile


class PDFReader:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path

    def read_pdf(self):
        """
        Read the PDF and extract text and tables from each page.
        Returns a list of dictionaries with page number, text content, and tables.
        """
        result = []
        
        with pdfplumber.open(self.pdf_path) as pdf:
            total_pages = len(pdf.pages)
            
            for page_number in range(total_pages):
                page_data = self.read_page(page_number)
                result.append(page_data)
        
        return result
    def read_page(self, page_number):
        """
        Read a specific page and extract text and tables.

        Args:
            page_number: 0-based page number

        Returns:
            dict: Contains page number, text content, lattice tables, and stream tables
        """
        camelot_page_number = page_number + 1

        text_content = self.extract_text(page_number)
        lattice_tables_data = self.extract_tables(page_number)
        stream_tables_data = self.extract_stream_tables(page_number)

        return {
            "page": camelot_page_number,  # 1-based page number for consistency
            "text_content": text_content or "",
            "lattice_tables": lattice_tables_data,
            "stream_tables": stream_tables_data
        }

    def extract_text(self, page_number):
        """Extract text from a specific page."""
        with pdfplumber.open(self.pdf_path) as pdf:
            return pdf.pages[page_number].extract_text()

    def extract_stream_tables(self, page_number):
        """Extract stream tables from a specific page using camelot."""
        camelot_page_number = page_number + 1
        try:
            tables = camelot.read_pdf(
                self.pdf_path, 
                flavor='stream', 
                pages=str(camelot_page_number)
            )
            return [table.df.values.tolist() for table in tables]
        except Exception as e:
            print(f"Warning: Could not extract stream tables from page {camelot_page_number}: {e}")
            return []

    def extract_tables(self, page_number):
        """Extract lattice tables from a specific page using camelot and return as matrices (list of lists)."""
        camelot_page_number = page_number + 1
        try:
            tables = camelot.read_pdf(
                self.pdf_path, 
                flavor='lattice', 
                pages=str(camelot_page_number)
            )
            return [table.df.values.tolist() for table in tables]
        except Exception as e:
            print(f"Warning: Could not extract lattice tables from page {camelot_page_number}: {e}")
            return []
    def table_matrix_to_markdown(self, table_matrix, header=True):
        """
        Convert a table in matrix (list of lists) format to a markdown table string.
        If header=True, the first row is treated as the header. If header=False, all rows are treated as data.
        """
        if not table_matrix or not any(table_matrix):
            return ""
        if header and len(table_matrix) > 0:
            header_row = table_matrix[0]
            data_rows = table_matrix[1:]
            md = "| " + " | ".join(str(cell).replace("\n", "<br>") if cell is not None else "" for cell in header_row) + " |\n"
            md += "| " + " | ".join("---" for _ in header_row) + " |\n"
            for row in data_rows:
                md += "| " + " | ".join(str(cell).replace("\n", "<br>") if cell is not None else "" for cell in row) + " |\n"
        else:
            # No header: treat all rows as data, use generic column names
            num_cols = max(len(row) for row in table_matrix)
            md = "| " + " | ".join(f"col{i+1}" for i in range(num_cols)) + " |\n"
            md += "| " + " | ".join("---" for _ in range(num_cols)) + " |\n"
            for row in table_matrix:
                # Pad row if it's shorter than num_cols
                padded_row = list(row) + [""] * (num_cols - len(row))
                md += "| " + " | ".join(str(cell).replace("\n", "<br>") if cell is not None else "" for cell in padded_row) + " |\n"
        return md

    
    
    def read_pdf_as_markdown(self):
        pdf_data = self.read_pdf()
        result = ""
        for page in pdf_data:
            result += f"\n\n## Page {page['page']}"
            result += "\n\n" + page["text_content"]
            lattice_tables = [self.table_matrix_to_markdown(table) for table in page["lattice_tables"]]
            stream_tables = [self.table_matrix_to_markdown(table) for table in page["stream_tables"]]
            result += "\n\n Lattice Tables:\n\n"
            for i, table in enumerate(lattice_tables):
                result += f"\n\n Table {i+1}:\n\n"
                result += table + "\n\n"
            result += "\n\n Stream Tables:\n" 
            for i, table in enumerate(stream_tables):
                result += f"\n\n Table {i+1}:\n\n"
                result += table + "\n\n"
            result += "$"*40 + "\n\n"
        return result.replace("", "- ").replace("", "\t- ")

