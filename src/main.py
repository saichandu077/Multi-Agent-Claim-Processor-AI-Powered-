# src/main.py

from fastapi import FastAPI, UploadFile, File, HTTPException
from typing import List
import uvicorn

from src.pipeline import run_pipeline
from src.schemas import BatchClaimResponse

app = FastAPI(
    title="HealthPay Batch Claim Processor",
    description="An AI pipeline to process batches of medical insurance claim documents."
)

@app.post("/process-claim-batch", response_model=BatchClaimResponse)
async def process_claim_batch(files: List[UploadFile] = File(...)):
    """
    Accepts a batch of PDF files, groups them by claim, processes each claim,
    and returns a list of results.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files were uploaded.")

    try:
        print(f"[INFO] Received {len(files)} files")
        files_data = [await file.read() for file in files]
        filenames = [file.filename for file in files]

        for i, fname in enumerate(filenames):
            print(f"--- File {i + 1}/{len(filenames)}: {fname} ---")

        result = await run_pipeline(files_data, filenames)

        if not result.processed_claims:
            print("[WARN] run_pipeline returned an empty processed_claims list.")
        else:
            for claim in result.processed_claims:
                print("[SUCCESS] Processed claim:", claim.document_data)

        return result

    except Exception as e:
        import traceback
        print(f"[CRITICAL] Unhandled exception: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="An internal error occurred during claim processing.")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
