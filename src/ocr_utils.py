import pytesseract
from pdf2image import convert_from_path

POPPLER_PATH = r"C:\poppler\Library\bin"
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_hospital_name_from_pdf_header(pdf_path: str) -> str:
    try:
        images = convert_from_path(pdf_path, first_page=1, last_page=1, poppler_path=POPPLER_PATH)
        if images:
            ocr_text = pytesseract.image_to_string(images[0])
            for line in ocr_text.splitlines():
                if "hospital" in line.lower() or "clinic" in line.lower():
                    return line.strip()
        return None
    except Exception as e:
        print(f"[OCR HEADER ERROR] {e}")
        return None
