from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(String, default="researcher")  # researcher | admin
    created_at = Column(DateTime, default=datetime.utcnow)

    datasets = relationship("Dataset", back_populates="owner")


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    location_name = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    sample_type = Column(String, nullable=True)  # water, soil, sediment...
    status = Column(String, default="uploaded")  # uploaded|processing|completed|failed
    file_name = Column(String, nullable=True)
    total_reads = Column(Integer, default=0)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="datasets")
    observations = relationship("SpeciesObservation", back_populates="dataset", cascade="all, delete-orphan")
    sites = relationship("SamplingSite", back_populates="dataset", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="dataset", cascade="all, delete-orphan")


class TaxonomyNode(Base):
    """Reference taxonomy tree (kingdom -> phylum -> class -> order -> family -> genus -> species)."""
    __tablename__ = "taxonomy_nodes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    rank = Column(String, nullable=False)  # kingdom, phylum, class, order, family, genus, species
    parent_id = Column(Integer, ForeignKey("taxonomy_nodes.id"), nullable=True)
    iucn_status = Column(String, nullable=True)  # LC, NT, VU, EN, CR, EW, EX, DD, NE
    common_name = Column(String, nullable=True)

    parent = relationship("TaxonomyNode", remote_side=[id], backref="children")


class SamplingSite(Base):
    """A real geographic collection point. A dataset can span several sites,
    which is what makes per-species mapping possible (dataset-level lat/lng
    can only place the whole survey at one dot)."""
    __tablename__ = "sampling_sites"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    collected_at = Column(DateTime, nullable=True)

    dataset = relationship("Dataset", back_populates="sites")
    observations = relationship("SpeciesObservation", back_populates="site")


class SpeciesObservation(Base):
    """A single identified taxon within a dataset, with abundance for diversity math."""
    __tablename__ = "species_observations"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    site_id = Column(Integer, ForeignKey("sampling_sites.id"), nullable=True)
    taxonomy_node_id = Column(Integer, ForeignKey("taxonomy_nodes.id"), nullable=True)
    species_name = Column(String, nullable=False)
    read_count = Column(Integer, default=0)
    confidence = Column(Float, default=0.0)  # 0-1 model confidence
    is_novel_candidate = Column(Boolean, default=False)

    dataset = relationship("Dataset", back_populates="observations")
    site = relationship("SamplingSite", back_populates="observations")
    taxonomy_node = relationship("TaxonomyNode")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=True)
    shannon_index = Column(Float, nullable=True)
    simpson_index = Column(Float, nullable=True)
    evenness = Column(Float, nullable=True)
    species_richness = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    dataset = relationship("Dataset", back_populates="reports")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String, nullable=False)  # user | assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
