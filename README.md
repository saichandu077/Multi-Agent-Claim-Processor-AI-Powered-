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

1. Install Dependencies
  pip install -r requirements.txt

2.Configure Environment Variables
  Create a .env file in the root directory:
     OPENAI_API_KEY=your-api-key-here
     
3. Install External Tools
  🔠 Tesseract OCR (for image-based text extraction)

  📄 Poppler for Windows (for PDF rendering)

  Make sure both are added to your system PATH or referenced correctly in agents.py.


 How It Works (Step-by-Step)
  Step 1: Upload PDFs
    Send a POST request to /process-claim-batch with one or more .pdf files.

  Step 2: Classification
    Each document is passed through a GPT-based classification agent to detect type:
      bill
      discharge_summary
      consolidated_claim
      id_card

  Step 3: Extraction (Node 1)
    A document-type-specific LLM prompt is used to extract fields like:
      Patient Name
      Hospital Name
      Total Amount
      Diagnosis
      Policy ID
      Admission/Discharge Dates
      Date of Service

  Step 4: Fallback Enhancements
      If any field is missing:
      OCR is used to scan PDF headers and extract hospital names.
      Regex is used for Policy IDs (MaxID, UHID, etc.).
      Dates are normalized from DD/MM/YYYY or YYYY/MM/DD format.
      Amounts are extracted from "Grand Total", "Net Payable", etc.

  Step 5: Validation (Node 2)
      Checks for missing fields.
      Ensures logical consistency (e.g., date_of_service falls between admission and discharge).
      Final decision:  approved or  rejected.

  Sample Response json Copy code
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
  Prompt Library
    BILL_EXTRACTION_PROMPT:
        You are a structured data extractor for hospital bill PDFs. Extract the following               fields from the document text. Follow these rules:
        Return a valid JSON object with these exact keys:
        - "patient_name": string or null
        - "hospital_name": string or null
        - "total_amount": number or null
        - "date_of_service": string (YYYY-MM-DD) or null
        - "policy_id": string or null
        Rules:
        1. DO NOT include any explanation, headers, or extra text — ONLY return the JSON object.
        2. If a field is not present or uncertain, use `null`.
        3. `total_amount` must be numeric (e.g., 447051 or 12500.50). Do not include currency           symbols or commas.
        4. `date_of_service` must be a valid date (e.g., "2025-02-07").
        5. Look for policy-related identifiers like: "Policy No", "Policy Number", "MaxID",             "UHID", "CCN", "Claim Number", or "Episode ID" for `policy_id`.
        6. Extract the clean hospital name — ignore GST numbers, IDs, etc.
        
   DISCHARGE_SUMMARY_EXTRACTION_PROMPT
      You are a structured data extractor for medical discharge summaries. Extract the                following fields.
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
      4. Clean hospital name — exclude GST, ID, etc.
      5. For diagnosis, prefer text under headings like "DIAGNOSIS", "FINAL DIAGNOSIS" and            merge up to 3 lines.
      
  CLASSIFICATION_PROMPT
      You are a document classification system for medical claim PDFs.
      Return one of: 'bill', 'discharge_summary', 'id_card', 'consolidated_claim'.
      Prefer 'consolidated_claim' if both financial and clinical info are present.
      
  Folder Structure
      src/
      ├── main.py                  # FastAPI entrypoint
      ├── agents.py                # Extraction logic & LLM prompts
      ├── pipeline.py              # LangGraph state machine
      ├── schemas.py               # Pydantic models
      ├── utils.py                 # OCR, PDF parsing, fallback helpers






