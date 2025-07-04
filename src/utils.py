from pdf2image import convert_from_bytes
from PyPDF2 import PdfReader
import pytesseract
import io
import pdfplumber  # ✅ newly added

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"C:\poppler\poppler-24.08.0\Library\bin"


def extract_text_from_pdf_by_page(file_bytes: bytes) -> list[str]:
    try:
        # ✅ First try: use pdfplumber (preferred over PyPDF2)
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            text_by_page = [page.extract_text() or "" for page in pdf.pages]

        text_combined = "".join(text_by_page).strip()
        if text_combined and len(text_combined) > 100:
            print("[INFO] Extracted text using pdfplumber (non-OCR)")
            return text_by_page

        raise ValueError("Insufficient text from pdfplumber, falling back to OCR")

    except Exception as e:
        print(f"[WARN] pdfplumber failed or empty: {e}")
        try:
            # ✅ Final fallback: OCR
            images = convert_from_bytes(file_bytes, poppler_path=POPPLER_PATH)
            print("[INFO] Extracting text using OCR fallback")
            return [pytesseract.image_to_string(img) for img in images]
        except Exception as ocr_error:
            print(f"[OCR ERROR] Failed to extract with OCR: {ocr_error}")
            return []
