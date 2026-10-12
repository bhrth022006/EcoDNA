from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=List[schemas.UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.require_admin),
):
    return db.query(models.User).all()


@router.get("/stats")
def platform_stats(
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.require_admin),
):
    return {
        "total_users": db.query(models.User).count(),
        "total_datasets": db.query(models.Dataset).count(),
        "total_species_observations": db.query(models.SpeciesObservation).count(),
        "total_reports": db.query(models.Report).count(),
    }
