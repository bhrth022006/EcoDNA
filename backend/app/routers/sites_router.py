from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth
from app.utils import biodiversity_calc as calc
from app.utils.common_names import get_common_name

router = APIRouter(prefix="/api/datasets", tags=["sites"])


@router.get("/{dataset_id}/sites", response_model=List[schemas.SamplingSiteOut])
def get_sites(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """Sampling sites for a dataset with real coordinates and per-site
    diversity computed from that site's own observations."""
    dataset = (
        db.query(models.Dataset)
        .filter(models.Dataset.id == dataset_id, models.Dataset.owner_id == current_user.id)
        .first()
    )
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    sites = (
        db.query(models.SamplingSite)
        .filter(models.SamplingSite.dataset_id == dataset_id)
        .all()
    )

    results = []
    for site in sites:
        observations = site.observations
        counts = [o.read_count for o in observations]
        dominant = (
            max(observations, key=lambda o: o.read_count).species_name
            if observations else None
        )
        results.append(
            schemas.SamplingSiteOut(
                id=site.id,
                name=site.name,
                latitude=site.latitude,
                longitude=site.longitude,
                species_richness=calc.species_richness(counts),
                total_reads=sum(counts),
                shannon_index=calc.shannon_index(counts),
                dominant_species=dominant,
                dominant_species_common=get_common_name(dominant) if dominant else None,
                species=[
                    schemas.SiteSpeciesOut(
                        species_name=o.species_name,
                        common_name=get_common_name(o.species_name),
                        read_count=o.read_count,
                        confidence=o.confidence,
                    )
                    for o in sorted(observations, key=lambda o: o.read_count, reverse=True)
                ],
            )
        )
    return results
