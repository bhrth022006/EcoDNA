"""
Wraps the trained k-mer RandomForest classifier (ml_model/model.joblib)
as a route on the main API, so the frontend only ever talks to one port.

Model provenance: trained on a SYNTHETIC reference dataset (see
ml_model/generate_data.py) — a real trained model, but demo-grade data.
Swap in real GenBank/BOLD reference barcodes and re-run
ml_model/train_model.py before using this for anything beyond a prototype.
"""
import re
from pathlib import Path

import joblib
import numpy as np
from fastapi import APIRouter
from pydantic import BaseModel

from ml_model.train_model import kmer_features
from app.utils.common_names import get_common_name

router = APIRouter(prefix="/api", tags=["prediction"])

MODEL_PATH = Path(__file__).resolve().parent.parent.parent / "ml_model" / "model.joblib"
_bundle = None
_clf = None
_le = None


def _load_model():
    global _bundle, _clf, _le
    if _bundle is None:
        _bundle = joblib.load(MODEL_PATH)
        _clf = _bundle["model"]
        _le = _bundle["label_encoder"]
    return _bundle, _clf, _le


class SequenceIn(BaseModel):
    sequence: str


def clean_sequence(raw: str) -> str:
    lines = [l for l in raw.splitlines() if not l.startswith(">")]
    seq = "".join(lines)
    return re.sub(r"[^ACGTacgt]", "", seq).upper()


@router.post("/predict")
def predict(payload: SequenceIn):
    bundle, clf, le = _load_model()
    seq = clean_sequence(payload.sequence)
    if len(seq) < 10:
        return {"error": "Sequence too short after cleaning (need at least 10 bases)."}

    feat = kmer_features(seq).reshape(1, -1)
    probs = clf.predict_proba(feat)[0]
    top_idx = np.argsort(probs)[::-1][:5]

    results = [
        {
            "species": le.classes_[i],
            "common_name": get_common_name(le.classes_[i]),
            "confidence": round(float(probs[i]), 4),
        }
        for i in top_idx
    ]

    importances = clf.feature_importances_
    kmer_list = bundle["kmer_list"]
    present_kmers = {seq[i:i + bundle["k"]] for i in range(len(seq) - bundle["k"] + 1)}
    ranked = sorted(
        ((kmer_list[i], importances[i]) for i in range(len(kmer_list)) if kmer_list[i] in present_kmers),
        key=lambda x: x[1], reverse=True
    )[:8]

    return {
        "predictions": results,
        "sequence_length": len(seq),
        "influential_kmers": [{"kmer": k, "importance": round(float(v), 5)} for k, v in ranked],
    }


@router.get("/predict/health")
def predict_health():
    _, _, le = _load_model()
    return {"status": "ok", "species_count": len(le.classes_)}
