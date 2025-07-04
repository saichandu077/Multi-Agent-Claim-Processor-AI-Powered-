# src/pipeline.py

from typing import List, TypedDict, Dict
from langgraph.graph import StateGraph, END
from collections import defaultdict

from src.agents import classify_document, targeted_extraction_agent, validation_agent
from src.utils import extract_text_from_pdf_by_page
from src.schemas import BatchClaimResponse, ClaimResult, InitialExtraction, ConsolidatedClaimData, Bill, DischargeSummary, IDCard


class GraphState(TypedDict):
    files_data: List[bytes]
    filenames: List[str]
    initial_extractions: List[InitialExtraction]
    batch_results: List[ClaimResult]


MODEL_MAP = {
    "bill": Bill,
    "discharge_summary": DischargeSummary,
    "id_card": IDCard
}


async def initial_extraction_node(state: GraphState):
    """Node 1: Performs targeted extraction and returns a list of Pydantic objects."""
    print("--- Node 1: Targeted Extraction ---")
    all_docs = []

    for i, file_bytes in enumerate(state['files_data']):
        filename = state['filenames'][i]
        full_text = "\n".join(extract_text_from_pdf_by_page(file_bytes))

        doc_type = await classify_document(full_text, filename)
        # Force classification to consolidated_claim if needed
        doc_type = "consolidated_claim"

        print(f"  -> File '{filename}' classified as '{doc_type}'")

        extracted = []

        if doc_type == "consolidated_claim":
            print("  -> Extracting both bill and discharge_summary from consolidated_claim")
            bill_model = await targeted_extraction_agent(full_text, Bill, "bill", file_bytes)
            summary_model = await targeted_extraction_agent(full_text, DischargeSummary, "discharge_summary", file_bytes)

            if bill_model:
                extracted.append(bill_model)
            if summary_model:
                extracted.append(summary_model)

        elif doc_type in MODEL_MAP:
            model = MODEL_MAP[doc_type]
            validated_doc = await targeted_extraction_agent(full_text, model, doc_type, file_bytes)

            if validated_doc:
                extracted.append(validated_doc)
            else:
                print(f"  -> WARNING: Extraction failed or returned invalid data for '{filename}'. Skipping.")
        else:
            print(f"  -> Skipping unsupported document type: '{doc_type}'")

        all_docs.extend(extracted)

    return {"initial_extractions": all_docs}


async def validate_node(state: GraphState):
    """Node 2: Validates documents independently and builds claim results."""
    print("\n--- Node 2: Validating Individually Extracted Claims ---")
    initial_extractions = state['initial_extractions']

    if not initial_extractions:
        print("  -> No valid documents were extracted. Ending pipeline.")
        return {"batch_results": []}

    claim_groups = defaultdict(list)
    for doc in initial_extractions:
        if doc.patient_name:
            claim_groups[doc.patient_name].append(doc)

    final_results = []
    for identifier, docs in claim_groups.items():
        print(f"\n--- Processing Claim for: {identifier} ---")

        data = ConsolidatedClaimData()
        for doc in docs:
            doc_dict = doc.model_dump()
            for key, value in doc_dict.items():
                if value and getattr(data, key) is None:
                    setattr(data, key, value)

        validation_results = await validation_agent(data)

        if validation_results.missing_fields or validation_results.discrepancies:
            status, reason = "rejected", "Claim failed validation due to missing fields or discrepancies."
        else:
            status, reason = "approved", "All required data is present and consistent."

        final_results.append(ClaimResult(
            claim_identifier=identifier,
            document_data=data,
            validation=validation_results,
            claim_decision={"status": status, "reason": reason}
        ))

    return {"batch_results": final_results}


def build_graph():
    workflow = StateGraph(GraphState)
    workflow.add_node("initial_extraction", initial_extraction_node)
    workflow.add_node("validate", validate_node)
    workflow.set_entry_point("initial_extraction")
    workflow.add_edge("initial_extraction", "validate")
    workflow.add_edge("validate", END)
    return workflow.compile()


graph = build_graph()


async def run_pipeline(files_data: List[bytes], filenames: List[str]) -> BatchClaimResponse:
    initial_state = {"files_data": files_data, "filenames": filenames}
    final_state = await graph.ainvoke(initial_state)
    return BatchClaimResponse(processed_claims=final_state.get('batch_results', []))
