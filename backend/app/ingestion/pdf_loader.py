
import pdfplumber

class PDFLoader:
    def load(self, path: str) -> str:
        text = ""
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    text += f"\n\n{page_text.strip()}"
        return text