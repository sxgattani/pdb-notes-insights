from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api import sync, notes, features

settings = get_settings()

app = FastAPI(
    title="ProductBoard Insights",
    description="Read-only reporting system for ProductBoard notes",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sync.router, prefix="/api/v1")
app.include_router(notes.router, prefix="/api/v1")
app.include_router(features.router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "healthy"}
