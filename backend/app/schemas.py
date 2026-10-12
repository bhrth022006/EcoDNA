from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# ---------- Auth ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str]
    role: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Dataset ----------
class DatasetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    location_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    sample_type: Optional[str] = None


class DatasetOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    location_name: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    sample_type: Optional[str]
    status: str
    total_reads: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Species / Taxonomy ----------
class SpeciesObservationOut(BaseModel):
    id: int
    species_name: str
    read_count: int
    confidence: float
    is_novel_candidate: bool

    class Config:
        from_attributes = True


class TaxonomyNodeOut(BaseModel):
    id: int
    name: str
    rank: str
    common_name: Optional[str]
    iucn_status: Optional[str]

    class Config:
        from_attributes = True


# ---------- Sampling sites / geography ----------
class SiteSpeciesOut(BaseModel):
    species_name: str
    read_count: int
    confidence: float

    class Config:
        from_attributes = True


class SamplingSiteOut(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float
    species_richness: int
    total_reads: int
    shannon_index: float
    dominant_species: Optional[str]
    species: List[SiteSpeciesOut]


# ---------- Biodiversity ----------
class BiodiversityMetrics(BaseModel):
    dataset_id: int
    species_richness: int
    shannon_index: float
    simpson_index: float
    pielou_evenness: float
    total_reads: int
    dominant_species: Optional[str]


# ---------- Reports ----------
class ReportOut(BaseModel):
    id: int
    dataset_id: int
    title: str
    summary: Optional[str]
    shannon_index: Optional[float]
    simpson_index: Optional[float]
    evenness: Optional[float]
    species_richness: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True
# ---------- Add to app/schemas.py ----------
# Paste this class in anywhere with the other schemas (e.g. near ReportOut).

class ValidationReport(BaseModel):
    file_name: str
    total_sequences: int
    passed_quality_filtering: int
    duplicates_removed: int
    contaminant_removed: int
    below_length_excluded: int
    remaining_after_filtering: int
    warnings: List[str]


# ---------- Chat ----------
class ChatRequest(BaseModel):
    message: str
    dataset_id: Optional[int] = None


class ChatResponse(BaseModel):
    reply: str
