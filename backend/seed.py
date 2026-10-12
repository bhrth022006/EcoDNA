"""
Run with: python seed.py
Creates a demo user (demo@bioscope.ai / demo1234), a small reference
taxonomy tree, and one sample eDNA dataset with species abundances —
enough to exercise every endpoint and see real (non-zero) diversity numbers.
"""
from app.database import SessionLocal, Base, engine
from app import models, auth

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# --- demo user ---
existing = db.query(models.User).filter(models.User.email == "demo@bioscope.ai").first()
if not existing:
    demo_user = models.User(
        email="demo@bioscope.ai",
        hashed_password=auth.hash_password("demo1234"),
        full_name="Demo Researcher",
        role="admin",
    )
    db.add(demo_user)
    db.commit()
    db.refresh(demo_user)
else:
    demo_user = existing

# --- minimal taxonomy tree ---
if db.query(models.TaxonomyNode).count() == 0:
    animalia = models.TaxonomyNode(name="Animalia", rank="kingdom")
    db.add(animalia)
    db.commit()
    db.refresh(animalia)

    chordata = models.TaxonomyNode(name="Chordata", rank="phylum", parent_id=animalia.id)
    arthropoda = models.TaxonomyNode(name="Arthropoda", rank="phylum", parent_id=animalia.id)
    db.add_all([chordata, arthropoda])
    db.commit()
    db.refresh(chordata)
    db.refresh(arthropoda)

    actinopterygii = models.TaxonomyNode(name="Actinopterygii", rank="class", parent_id=chordata.id)
    db.add(actinopterygii)
    db.commit()
    db.refresh(actinopterygii)

    db.add_all([
        models.TaxonomyNode(
            name="Salmo salar", rank="species", parent_id=actinopterygii.id,
            common_name="Atlantic salmon", iucn_status="NT",
        ),
        models.TaxonomyNode(
            name="Gadus morhua", rank="species", parent_id=actinopterygii.id,
            common_name="Atlantic cod", iucn_status="VU",
        ),
    ])
    db.commit()

# --- sample dataset with abundances (mirrors the frontend's sample eDNA set) ---
if db.query(models.Dataset).filter(models.Dataset.owner_id == demo_user.id).count() == 0:
    dataset = models.Dataset(
        name="Coastal Water Sample — Site A",
        description="Surface water eDNA sample, 2L filtered, 0.22um membrane",
        location_name="Monterey Bay, CA",
        latitude=36.6002,
        longitude=-121.8947,
        sample_type="water",
        status="completed",
        owner_id=demo_user.id,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    # Three real sampling sites with genuine Monterey Bay coordinates,
    # so the map has actual geography to plot.
    site_defs = [
        ("Site A — Moss Landing Harbor", 36.8025, -121.7869, [
            ("Salmo salar", 2100, 0.97),
            ("Gadus morhua", 1650, 0.95),
            ("Mytilus edulis", 720, 0.93),
            ("Calanus finmarchicus", 310, 0.85),
        ]),
        ("Site B — Monterey Canyon Head", 36.7783, -121.8479, [
            ("Thunnus albacares", 1500, 0.91),
            ("Gadus morhua", 980, 0.94),
            ("Salmo salar", 1400, 0.96),
            ("Undescribed eukaryote sp.", 95, 0.42),
        ]),
        ("Site C — Point Pinos Kelp Forest", 36.6380, -121.9340, [
            ("Laminaria digitata", 410, 0.80),
            ("Homarus americanus", 1420, 0.88),
            ("Mytilus edulis", 260, 0.92),
            ("Salmo salar", 710, 0.95),
            ("Calanus finmarchicus", 330, 0.86),
        ]),
    ]

    total = 0
    for site_name, lat, lng, species_list in site_defs:
        site = models.SamplingSite(
            dataset_id=dataset.id, name=site_name, latitude=lat, longitude=lng
        )
        db.add(site)
        db.flush()
        for name, reads, conf in species_list:
            db.add(models.SpeciesObservation(
                dataset_id=dataset.id,
                site_id=site.id,
                species_name=name,
                read_count=reads,
                confidence=conf,
                is_novel_candidate=conf < 0.5,
            ))
            total += reads

    dataset.total_reads = total
    dataset.latitude = sum(s[1] for s in site_defs) / len(site_defs)
    dataset.longitude = sum(s[2] for s in site_defs) / len(site_defs)
    db.add(dataset)
    db.commit()

db.close()
print("Seed complete.")
print("Login with: demo@bioscope.ai / demo1234")
