# 🏥 HealthPay AI Medical Claim Processor

An AI-powered backend system for extracting, classifying, and validating hospital bill and discharge summary data from medical PDFs. Built using FastAPI, LangGraph, OpenAI GPT-4 Turbo, and OCR fallbacks, it enables fast and accurate medical claim processing for insurance companies and healthcare systems.

---

## 🚀 Project Objectives

- Automatically extract structured data from uploaded PDF claims.
- Handle various medical documents (bills, discharge summaries, ID cards, consolidated).
- Apply fallback extraction (OCR, regex) for missing information.
- Validate claim data for consistency and completeness.
- Return structured claim results with approval/rejection decision.

---

## 🧠 Features

- ✅ Multi-document extraction (bills + discharge summaries)
- ✅ Classification (`bill`, `discharge_summary`, `consolidated_claim`, `id_card`)
- ✅ Field extraction using GPT-4 Turbo
- ✅ Fallback logic (OCR, regex for hospital name, date, diagnosis, policy ID)
- ✅ LangGraph-based pipeline with modular validation
- ✅ FastAPI endpoint for PDF batch processing
- ✅ JSON-based response with detailed validation

---

## 🧰 Tech Stack

| Layer              | Tools / Libraries                            |
|--------------------|----------------------------------------------|
| AI Extraction      | OpenAI GPT-4 Turbo (`openai`)                |
| Backend API        | FastAPI, LangGraph                           |
| PDF Parsing        | pdfplumber, PyPDF2, pdf2image                |
| OCR Support        | pytesseract + Poppler                        |
| Schemas & Models   | Pydantic                                     |
| Dev IDE            | Cursor.ai                                    |

---

## 📦 Folder Structure

src/
├── agents.py # LLM prompts & extraction logic
├── main.py # FastAPI app
├── pipeline.py # LangGraph state machine
├── schemas.py # Pydantic models
├── utils.py # OCR and PDF fallback helpers

yaml
Copy code

---

## ⚙️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/healthpay-claim-processor.git
cd healthpay-claim-processor
2. Install Dependencies
bash
Copy code
pip install -r requirements.txt
3. Add OpenAI API Key
Create a .env file:

env
Copy code
OPENAI_API_KEY=your_openai_key_here
4. Install Poppler & Tesseract (for OCR)
Poppler for Windows

Tesseract OCR

Add their bin paths to your system or configure directly in agents.py.

🚀 How It Works
Step 1: Upload PDFs
You upload one or more .pdf files via:

arduino
Copy code
POST /process-claim-batch
Step 2: Document Classification
Each PDF is classified into one of:

bill

discharge_summary

consolidated_claim

id_card

Step 3: GPT-based Field Extraction
Uses tailored prompts for each document type to extract:

patient_name

hospital_name

total_amount

diagnosis

policy_id

admission_date

discharge_date

date_of_service

Step 4: Fallback Enhancements (if missing)
✅ OCR (Tesseract) on headers for hospital_name

✅ Regex for policy_id (e.g., MaxID, Episode ID)

✅ Manual date parsing from strings like “03/02/2025”

✅ Total amount from “Grand Total” or “Net Payable”

✅ Diagnosis from headings like “FINAL DIAGNOSIS”

Step 5: Validation + Response
Each claim is validated for:

required fields

consistency (e.g., date of service within admission/discharge window)

Then a decision is returned:

json
Copy code
{
  "status": "approved" | "rejected",
  "reason": "..."
}
🧠 Prompts Used
🧾 BILL_EXTRACTION_PROMPT
text
Copy code
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
3. `total_amount` must be numeric.
4. Prefer fields like “Bill Date”, “Date of Service”, “Invoice Date”.
5. Look for identifiers: "MaxID", "UHID", "Policy Number", "Claim No", etc.
📄 DISCHARGE_SUMMARY_EXTRACTION_PROMPT
text
Copy code
You are a structured data extractor for medical discharge summaries. Extract the following fields.

Return a valid JSON object with these exact keys:
- "patient_name": string or null
- "hospital_name": string or null
- "diagnosis": string or null
- "admission_date": string (YYYY-MM-DD) or null
- "discharge_date": string (YYYY-MM-DD) or null

Rules:
1. DO NOT add any intro or text outside JSON.
2. For diagnosis, prefer "FINAL DIAGNOSIS" or "DIAGNOSIS".
3. Normalize all dates to "YYYY-MM-DD".
🧠 CLASSIFICATION_PROMPT
text
Copy code
You are a document classification system for medical claim PDFs.
Return one of: 'bill', 'discharge_summary', 'id_card', 'consolidated_claim'.
Prefer 'consolidated_claim' if both clinical and financial info are present.
🧪 Sample Output
json
Copy code
{
  "processed_claims": [
    {
      "claim_identifier": "Mary Philo",
      "document_data": {
        "hospital_name": "Fortis Hospitals Ltd Bannerghatta Road",
        "total_amount": 449564,
        "date_of_service": "2025-02-07",
        "patient_name": "Mary Philo",
        "diagnosis": "TYPHOID FEVER",
        "admission_date": "2025-02-07",
        "discharge_date": null,
        "policy_id": "41010250100000130-00"
      },
      "validation": {
        "missing_fields": ["discharge_date"],
        "discrepancies": []
      },
      "claim_decision": {
        "status": "rejected",
        "reason": "Claim failed validation due to missing fields or discrepancies."
      }
    }
  ]
}
🧠 Custom Fallback Logic
hospital_name → fallback via OCR on header (Tesseract)

policy_id → extracted using MaxID, UHID, CCN, etc.

admission/discharge_date → regex + normalization

total_amount → from Grand Total / Net Payable lines

diagnosis → from "DIAGNOSIS" heading using up to 3 lines
