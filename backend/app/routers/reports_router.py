from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth
from app.utils import biodiversity_calc as calc

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("/{dataset_id}/generate", response_model=schemas.ReportOut)
def generate_report(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    dataset = (
        db.query(models.Dataset)
        .filter(models.Dataset.id == dataset_id, models.Dataset.owner_id == current_user.id)
        .first()
    )
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    observations = (
        db.query(models.SpeciesObservation)
        .filter(models.SpeciesObservation.dataset_id == dataset_id)
        .all()
    )
    if not observations:
        raise HTTPException(status_code=400, detail="No species data to report on")

    counts = [o.read_count for o in observations]
    richness = calc.species_richness(counts)
    shannon = calc.shannon_index(counts)
    simpson = calc.simpson_index(counts)
    evenness = calc.pielou_evenness(counts)
    dominant = max(observations, key=lambda o: o.read_count).species_name

    summary = (
        f"Dataset '{dataset.name}' contains {richness} distinct taxa across "
        f"{sum(counts)} reads. Shannon diversity index is {shannon}, indicating "
        f"{'high' if shannon > 2.5 else 'moderate' if shannon > 1.5 else 'low'} community diversity. "
        f"The dominant taxon by read abundance is {dominant}."
    )

    report = models.Report(
        dataset_id=dataset_id,
        title=f"Biodiversity Report — {dataset.name}",
        summary=summary,
        shannon_index=shannon,
        simpson_index=simpson,
        evenness=evenness,
        species_richness=richness,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("/{dataset_id}", response_model=List[schemas.ReportOut])
def list_reports(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    return db.query(models.Report).filter(models.Report.dataset_id == dataset_id).all()
