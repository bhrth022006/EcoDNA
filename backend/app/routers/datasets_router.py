import csv
import io
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.post("", response_model=schemas.DatasetOut)
def create_dataset(
    payload: schemas.DatasetCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    dataset = models.Dataset(**payload.model_dump(), owner_id=current_user.id, status="uploaded")
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


@router.get("", response_model=List[schemas.DatasetOut])
def list_datasets(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    return db.query(models.Dataset).filter(models.Dataset.owner_id == current_user.id).all()


@router.get("/{dataset_id}", response_model=schemas.DatasetOut)
def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    dataset = _get_owned_dataset(dataset_id, db, current_user)
    return dataset


@router.delete("/{dataset_id}")
def delete_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    dataset = _get_owned_dataset(dataset_id, db, current_user)
    db.delete(dataset)
    db.commit()
    return {"detail": "deleted"}


@router.post("/{dataset_id}/upload", response_model=List[schemas.SpeciesObservationOut])
async def upload_species_csv(
    dataset_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Ingests a CSV of pipeline results.

    Required columns: species_name, read_count
    Optional columns: confidence, site_name, latitude, longitude

    When site_name/latitude/longitude are present, each distinct site becomes
    a SamplingSite row with real coordinates, and observations are linked to
    it — that's what makes the geographic map genuinely geographic rather
    than one dot per dataset.

    This stands in for what a real Kraken2/BLAST/DADA2 pipeline would output —
    see the architecture doc for wiring an actual pipeline worker here.
    """
    dataset = _get_owned_dataset(dataset_id, db, current_user)

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    raw = await file.read()
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    fieldnames = set(reader.fieldnames or [])
    required_cols = {"species_name", "read_count"}
    if not required_cols.issubset(fieldnames):
        raise HTTPException(
            status_code=400,
            detail=f"CSV must include columns: {', '.join(required_cols)}",
        )

    has_geo = {"site_name", "latitude", "longitude"}.issubset(fieldnames)

    # Replace any existing observations and sites for this dataset
    db.query(models.SpeciesObservation).filter(
        models.SpeciesObservation.dataset_id == dataset_id
    ).delete()
    db.query(models.SamplingSite).filter(
        models.SamplingSite.dataset_id == dataset_id
    ).delete()
    db.flush()

    site_cache = {}  # site_name -> SamplingSite
    created = []
    total_reads = 0

    for row in reader:
        read_count = int(row.get("read_count", 0) or 0)
        confidence = float(row.get("confidence", 0.9) or 0.9)

        site = None
        if has_geo:
            site_name = (row.get("site_name") or "").strip()
            lat_raw = (row.get("latitude") or "").strip()
            lng_raw = (row.get("longitude") or "").strip()
            if site_name and lat_raw and lng_raw:
                if site_name not in site_cache:
                    try:
                        lat = float(lat_raw)
                        lng = float(lng_raw)
                    except ValueError:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid coordinates for site '{site_name}': {lat_raw}, {lng_raw}",
                        )
                    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
                        raise HTTPException(
                            status_code=400,
                            detail=f"Coordinates out of range for site '{site_name}': {lat}, {lng}",
                        )
                    new_site = models.SamplingSite(
                        dataset_id=dataset_id, name=site_name, latitude=lat, longitude=lng
                    )
                    db.add(new_site)
                    db.flush()  # assign an id so observations can reference it
                    site_cache[site_name] = new_site
                site = site_cache[site_name]

        obs = models.SpeciesObservation(
            dataset_id=dataset_id,
            site_id=site.id if site else None,
            species_name=row["species_name"].strip(),
            read_count=read_count,
            confidence=confidence,
        )
        db.add(obs)
        created.append(obs)
        total_reads += read_count

    # If the CSV carried coordinates, centre the dataset on its sites
    if site_cache:
        lats = [s.latitude for s in site_cache.values()]
        lngs = [s.longitude for s in site_cache.values()]
        dataset.latitude = sum(lats) / len(lats)
        dataset.longitude = sum(lngs) / len(lngs)

    dataset.status = "completed"
    dataset.total_reads = total_reads
    dataset.file_name = file.filename
    db.add(dataset)
    db.commit()

    for obs in created:
        db.refresh(obs)

    return created


@router.get("/{dataset_id}/species", response_model=List[schemas.SpeciesObservationOut])
def get_species(
    dataset_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    _get_owned_dataset(dataset_id, db, current_user)
    return (
        db.query(models.SpeciesObservation)
        .filter(models.SpeciesObservation.dataset_id == dataset_id)
        .order_by(models.SpeciesObservation.read_count.desc())
        .all()
    )


def _get_owned_dataset(dataset_id: int, db: Session, user: models.User) -> models.Dataset:
    dataset = (
        db.query(models.Dataset)
        .filter(models.Dataset.id == dataset_id, models.Dataset.owner_id == user.id)
        .first()
    )
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset
