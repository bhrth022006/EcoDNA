from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth
from app.utils import biodiversity_calc as calc
from app.utils.common_names import get_common_name

router = APIRouter(prefix="/api/biodiversity", tags=["biodiversity"])


@router.get("/{dataset_id}", response_model=schemas.BiodiversityMetrics)
def get_metrics(
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
        raise HTTPException(status_code=400, detail="No species data for this dataset yet")

    counts = [o.read_count for o in observations]
    dominant = max(observations, key=lambda o: o.read_count).species_name

    return schemas.BiodiversityMetrics(
        dataset_id=dataset_id,
        species_richness=calc.species_richness(counts),
        shannon_index=calc.shannon_index(counts),
        simpson_index=calc.simpson_index(counts),
        pielou_evenness=calc.pielou_evenness(counts),
        total_reads=sum(counts),
        dominant_species=dominant,
        dominant_species_common=get_common_name(dominant),
    )
