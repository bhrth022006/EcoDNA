from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from app import models, schemas, auth
from app.utils.fastq_validate import validate_fastq

router = APIRouter(prefix="/api", tags=["validation"])


@router.post("/validate-fastq", response_model=schemas.ValidationReport)
async def validate_fastq_upload(
    file: UploadFile = File(...),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Real FASTQ quality-control pass — no simulated numbers. Parses the
    uploaded file, decodes actual Phred quality scores, finds real exact
    duplicates, and flags reads below a minimum length or matching a
    placeholder contaminant screen (see fastq_validate.py for what a real
    host-DNA filter would need instead).

    This is deliberately independent of dataset creation: run it on a raw
    sequencer file *before* deciding whether to turn it into a dataset via
    POST /api/datasets and /api/datasets/{id}/upload.
    """
    if not (file.filename.endswith(".fastq") or file.filename.endswith(".fq")):
        raise HTTPException(status_code=400, detail="Only .fastq/.fq files are supported")

    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File isn't valid UTF-8 text — is this actually a FASTQ file?")

    try:
        result = validate_fastq(text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return schemas.ValidationReport(
        file_name=file.filename,
        total_sequences=result.total_sequences,
        passed_quality_filtering=result.passed_quality_filtering,
        duplicates_removed=result.duplicates_removed,
        contaminant_removed=result.contaminant_removed,
        below_length_excluded=result.below_length_excluded,
        remaining_after_filtering=result.remaining_after_filtering,
        warnings=result.warnings,
    )
