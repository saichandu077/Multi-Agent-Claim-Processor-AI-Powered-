# src/schemas.py

from pydantic import BaseModel, Field
from typing import List, Optional, Union

# --- Initial Extraction Models ---
# We make these fields optional to gracefully handle cases where the LLM can't find a value.
# This prevents the Pydantic validation from crashing the pipeline.
class Bill(BaseModel):
    patient_name: Optional[str] = None
    hospital_name: Optional[str] = None
    total_amount: Optional[float] = None
    date_of_service: Optional[str] = None
    policy_id: Optional[str] = None

class DischargeSummary(BaseModel):
    patient_name: Optional[str] = None
    hospital_name: Optional[str] = None
    diagnosis: Optional[str] = None
    admission_date: Optional[str] = None
    discharge_date: Optional[str] = None

class IDCard(BaseModel):
    patient_name: Optional[str] = None
    policy_id: Optional[str] = None

InitialExtraction = Union[Bill, DischargeSummary, IDCard]

# --- Final Consolidated Model (remains the same) ---
class ConsolidatedClaimData(BaseModel):
    hospital_name: Optional[str] = None
    total_amount: Optional[float] = None
    date_of_service: Optional[str] = None
    patient_name: Optional[str] = None
    diagnosis: Optional[str] = None
    admission_date: Optional[str] = None
    discharge_date: Optional[str] = None
    policy_id: Optional[str] = None

# --- API Response Models (remain the same) ---
class Validation(BaseModel):
    missing_fields: List[str]
    discrepancies: List[str]

class ClaimDecision(BaseModel):
    status: str
    reason: str

class ClaimResult(BaseModel):
    claim_identifier: str
    document_data: ConsolidatedClaimData
    validation: Validation
    claim_decision: ClaimDecision

class BatchClaimResponse(BaseModel):
    processed_claims: List[ClaimResult]