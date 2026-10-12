from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.config import settings
from app.routers import (
    auth_router,
    datasets_router,
    biodiversity_router,
    taxonomy_router,
    reports_router,
    chat_router,
    admin_router,
    predict_router,
    sites_router,
    validate_router,
)

# Creates tables on first run. For real migrations, switch to Alembic
# (see architecture doc, section 'Database Migrations').
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="BioScope AI API",
    description="Backend for eDNA taxonomy identification and biodiversity assessment",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(datasets_router.router)
app.include_router(biodiversity_router.router)
app.include_router(taxonomy_router.router)
app.include_router(reports_router.router)
app.include_router(chat_router.router)
app.include_router(admin_router.router)
app.include_router(predict_router.router)
app.include_router(sites_router.router)
app.include_router(validate_router.router) 


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "bioscope-ai-backend"}
