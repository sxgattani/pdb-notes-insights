from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api import sync, notes, features, reports, exports, scheduler, auth
from app.scheduler import start_scheduler, shutdown_scheduler
from app.scheduler.sync_job import register_sync_job
from app.scheduler.export_job import register_export_job
from app.database import engine, Base
from app import models  # noqa: F401 - imports models to register them

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown events."""
    # Create database tables
    Base.metadata.create_all(bind=engine)

    # Startup
    register_sync_job()
    register_export_job()
    start_scheduler()

    yield

    # Shutdown
    shutdown_scheduler()


app = FastAPI(
    title="ProductBoard Insights",
    description="Read-only reporting system for ProductBoard notes",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sync.router, prefix="/api/v1")
app.include_router(notes.router, prefix="/api/v1")
app.include_router(features.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(exports.router, prefix="/api/v1")
app.include_router(scheduler.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "healthy"}
