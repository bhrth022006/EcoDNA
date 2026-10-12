from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, auth
from app.utils import biodiversity_calc as calc

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=schemas.ChatResponse)
def chat(
    payload: schemas.ChatRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Rule-based assistant grounded in the user's real dataset numbers.
    Swap this for a call to the Anthropic API (see architecture doc,
    section 'AI Chat Assistant') to get genuinely conversational answers —
    this keeps the endpoint working with zero external dependencies.
    """
    message = payload.message.lower().strip()
    reply = None

    if payload.dataset_id:
        dataset = (
            db.query(models.Dataset)
            .filter(
                models.Dataset.id == payload.dataset_id,
                models.Dataset.owner_id == current_user.id,
            )
            .first()
        )
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        observations = (
            db.query(models.SpeciesObservation)
            .filter(models.SpeciesObservation.dataset_id == payload.dataset_id)
            .all()
        )
        counts = [o.read_count for o in observations]

        if any(k in message for k in ["shannon", "diversity index"]):
            reply = f"The Shannon diversity index for '{dataset.name}' is {calc.shannon_index(counts)}."
        elif "simpson" in message:
            reply = f"Simpson's diversity index for '{dataset.name}' is {calc.simpson_index(counts)}."
        elif any(k in message for k in ["richness", "how many species", "species count"]):
            reply = f"'{dataset.name}' contains {calc.species_richness(counts)} distinct taxa."
        elif "dominant" in message or "most common" in message:
            if observations:
                top = max(observations, key=lambda o: o.read_count)
                reply = f"The most abundant taxon is {top.species_name} with {top.read_count} reads."
        elif "even" in message:
            reply = f"Pielou's evenness for '{dataset.name}' is {calc.pielou_evenness(counts)}."

    if reply is None:
        reply = (
            "I can answer questions about a dataset's diversity indices, species richness, "
            "or dominant taxa — pass a dataset_id and ask, e.g. 'what's the Shannon index?'"
        )

    db.add(models.ChatMessage(user_id=current_user.id, role="user", content=payload.message))
    db.add(models.ChatMessage(user_id=current_user.id, role="assistant", content=reply))
    db.commit()

    return schemas.ChatResponse(reply=reply)
