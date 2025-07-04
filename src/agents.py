import os
import json
import re
from datetime import datetime
from typing import List, Type, Optional
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv
from openai import AsyncOpenAI

from . import schemas

from pdf2image import convert_from_bytes
import pytesseract

load_dotenv()
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=90.0)

# --- PROMPTS ---

BILL_EXTRACTION_PROMPT = """
You are a structured data extractor for hospital bill PDFs. Extract the following fields from the document text. Follow these rules:

Return a valid JSON object with these exact keys:
- "patient_name": string or null
- "hospital_name": string or null
- "total_amount": number or null
- "date_of_service": string (YYYY-MM-DD) or null
- "policy_id": string or null

Rules:
1. DO NOT include any explanation, headers, or extra text — ONLY return the JSON object.
2. If a field is not present or uncertain, use `null`.
3. `total_amount` must be numeric (e.g., 447051 or 12500.50). Do not include currency symbols or commas.
4. `date_of_service` must be a valid date (e.g., "2025-02-07").
5. Look for policy-related identifiers like: "Policy No", "Policy Number", "MaxID", "UHID", "CCN", "Claim Number", or "Episode ID" for `policy_id`. Use the most relevant one.
6. For `hospital_name`, extract the clean name of the hospital. Ignore surrounding IDs, GST numbers, or unrelated organization info.
7. The hospital name is usually located at the top of the first page, possibly in a heading or logo area.
8. If multiple dates exist, prefer "Bill Date", "Date of Service", or "Invoice Date".
9. If diagnosis is not labeled, fallback to treatment/procedure label.
"""


DISCHARGE_SUMMARY_EXTRACTION_PROMPT = """
You are a structured data extractor for medical discharge summaries. Extract the following fields.

Return a valid JSON object with these exact keys:
- "patient_name": string or null
- "hospital_name": string or null
- "diagnosis": string or null
- "admission_date": string (YYYY-MM-DD) or null
- "discharge_date": string (YYYY-MM-DD) or null

Rules:
1. DO NOT add any introduction or text outside the JSON.
2. Use `null` if a field is missing.
3. Dates must be in the format "YYYY-MM-DD".
4. For `hospital_name`, extract the clean hospital name — usually found at the top of the document, sometimes embedded in logos or headings.
5. For diagnosis, prefer text under headings like "DIAGNOSIS", "FINAL DIAGNOSIS" and cleanly merge up to 3 lines.
"""


# --- CLASSIFICATION ---

async def classify_document(text: str, filename: str) -> str:
    prompt = """
You are a document classification system for medical claim PDFs.
Return one of: 'bill', 'discharge_summary', 'id_card', 'consolidated_claim'.
Prefer 'consolidated_claim' if both financial and clinical info are present.
"""
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Filename: {filename}\n\n{text[:8000]}"}
            ],
            temperature=0
        )
        result_content = response.choices[0].message.content
        if result_content is not None:
            result = result_content.strip().lower()
            return result if result in ['bill', 'discharge_summary', 'id_card', 'consolidated_claim'] else 'bill'
        else:
            print("[WARN] classify_document: No content returned from OpenAI.")
            return 'bill'
    except Exception as e:
        print(f"[ERROR] classify_document: {e}")
        return 'bill'

# --- FALLBACKS ---

import difflib  # add at the top with your imports

def fallback_hospital_name(text: str, file_bytes: Optional[bytes]) -> Optional[str]:
    known_keywords = {
        "max": "Max Healthcare",
        "max healthcare": "Max Healthcare",
        "sir ganga ram": "Sir Ganga Ram Hospital",
        "ganga ram": "Sir Ganga Ram Hospital",
        "apollo": "Apollo Hospital",
        "fortis": "Fortis Hospital",
        "aiims": "AIIMS"
    }

    # Text-based match
    for key, value in known_keywords.items():
        if key in text.lower():
            return value

    if file_bytes:
        try:
            image = convert_from_bytes(
                file_bytes,
                first_page=1,
                last_page=1,
                poppler_path=r"C:\poppler\poppler-24.08.0\Library\bin"
            )[0]
            width, height = image.size
            cropped = image.crop((0, 0, width, int(height * 0.15)))  # top 15%
            ocr_text = pytesseract.image_to_string(cropped).lower()

            print("[DEBUG] OCR top-crop text:\n", ocr_text)

            for key, value in known_keywords.items():
                if key in ocr_text:
                    return value

            # EXTRA: If 'healthcare' + 'maxid' is present, guess Max Healthcare
            if "healthcare" in ocr_text and "maxid" in text.lower():
                print("[INFO] Detected 'healthcare' and MaxID, assuming Max Healthcare")
                return "Max Healthcare"

        except Exception as e:
            print(f"[WARN] OCR fallback failed: {e}")

    return None

def extract_policy_id(text: str) -> Optional[str]:
    # Match MaxID (already working)
    match = re.search(r"MaxID\s*[:\-]?\s*([A-Z0-9./\-]+)", text, re.IGNORECASE)
    if match:
        print("[INFO] Policy ID extracted from MaxID")
        return match.group(1).strip()

    # New: Match 'Patient ID  :  VSLI.633928'
    match = re.search(r"Patient\s*ID\s*[:\-]?\s*([A-Z0-9./\-]+)", text, re.IGNORECASE)
    if match:
        print("[INFO] Policy ID extracted from Patient ID")
        return match.group(1).strip()

    # Existing fallback options
    match = re.search(
        r"(Episode\s*ID|UHID|Policy\s*(No|Number)|Claim\s*Number|CCN)[\s:]*([A-Z0-9./\-]+)",
        text, re.IGNORECASE
    )
    if match:
        print(f"[INFO] Policy ID extracted from label: {match.group(1)}")
        return match.group(3).strip()

    print("[WARN] No policy ID matched.")
    return None



def extract_date(text: str, labels: List[str]) -> Optional[str]:
    for label in labels:
        pattern = rf"{label}\s*[:\-]?\s*(\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{2,4}})"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return normalize_date(match.group(1))
    return None

def normalize_date(date_str: str) -> Optional[str]:
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except:
            continue
    return None

# --- EXTRACTION ---

async def targeted_extraction_agent(
    text: str,
    model: Type[BaseModel],
    doc_type: str,
    file_bytes: Optional[bytes] = None
) -> Optional[BaseModel]:
    prompt = BILL_EXTRACTION_PROMPT if doc_type == "bill" else DISCHARGE_SUMMARY_EXTRACTION_PROMPT
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Schema:\n{json.dumps(model.model_json_schema())}\n\nDocument:\n{text[:16000]}"}
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        content = response.choices[0].message.content
        if content is None:
            print("[ERROR] targeted_extraction_agent: No content returned from OpenAI.")
            return None
        data = json.loads(content)

        if not data.get("hospital_name"):
            hospital = fallback_hospital_name(text, file_bytes)
            if hospital:
                data["hospital_name"] = hospital

        if not data.get("policy_id") or data["policy_id"] == "0":
            data["policy_id"] = extract_policy_id(text)

        if not data.get("discharge_date"):
            data["discharge_date"] = extract_date(text, ["Discharge Date", "Discharged On"])

        if not data.get("admission_date"):
            data["admission_date"] = extract_date(text, ["Date of Admission", "Admission Date"])

        if not data.get("total_amount"):
            data["total_amount"] = extract_total_amount(text)

        if doc_type == "discharge_summary" and not data.get("diagnosis"):
            data["diagnosis"] = extract_diagnosis(text)

        return model(**data)

    except Exception as e:
        print(f"[ERROR] targeted_extraction_agent: {e}")
        return None

# --- VALIDATION ---

async def validation_agent(data: schemas.ConsolidatedClaimData) -> schemas.Validation:
    missing = [k for k, v in data.model_dump().items() if v is None]
    discrepancies = []
    try:
        if data.admission_date and data.discharge_date and data.date_of_service:
            if not (data.admission_date <= data.date_of_service <= data.discharge_date):
                discrepancies.append("Date of service outside admission/discharge range.")
    except:
        discrepancies.append("Date comparison failed.")
    return schemas.Validation(missing_fields=missing, discrepancies=discrepancies)

# --- Helper Extraction Functions (added to fix linter errors) ---
def extract_total_amount(text: str) -> Optional[float]:
    """Extracts the largest number in the text as a fallback for total_amount."""
    amounts = re.findall(r"[0-9]+(?:\\.[0-9]{1,2})?", text.replace(",", ""))
    if amounts:
        try:
            return float(max(amounts, key=lambda x: float(x)))
        except Exception as e:
            print(f"[WARN] extract_total_amount: {e}")
    return None

def extract_diagnosis(text: str) -> Optional[str]:
    """Fallback: Try to extract diagnosis section from text."""
    print("[DEBUG] Running fallback extract_diagnosis")
    # Look for headings like DIAGNOSIS or FINAL DIAGNOSIS
    match = re.search(r"(?:DIAGNOSIS|FINAL DIAGNOSIS)[:\-\s]*([\s\S]{0,200})", text, re.IGNORECASE)
    if match:
        diagnosis = match.group(1).strip().split("\n")[0:3]
        diagnosis_str = "; ".join([d.strip() for d in diagnosis if d.strip()])
        print("[INFO] Diagnosis extracted via fuzzy match.")
        return diagnosis_str if diagnosis_str else None
    print("[WARN] Diagnosis section not found in fallback.")
    return None
