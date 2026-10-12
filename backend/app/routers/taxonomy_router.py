from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth

router = APIRouter(prefix="/api/taxonomy", tags=["taxonomy"])


@router.get("", response_model=List[schemas.TaxonomyNodeOut])
def list_taxonomy(
    rank: Optional[str] = Query(None),
    parent_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    q = db.query(models.TaxonomyNode)
    if rank:
        q = q.filter(models.TaxonomyNode.rank == rank)
    if parent_id is not None:
        q = q.filter(models.TaxonomyNode.parent_id == parent_id)
    if search:
        like = f"%{search}%"
        q = q.filter(
            (models.TaxonomyNode.name.ilike(like))
            | (models.TaxonomyNode.common_name.ilike(like))
        )
    return q.all()


@router.get("/{node_id}/children", response_model=List[schemas.TaxonomyNodeOut])
def get_children(
    node_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    return db.query(models.TaxonomyNode).filter(models.TaxonomyNode.parent_id == node_id).all()
