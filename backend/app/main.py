from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import get_settings
from app.api import sync, notes, features, reports, scheduler, auth
from app.scheduler import start_scheduler, shutdown_scheduler
from app.scheduler.sync_job import register_sync_job
from app.database import engine, Base
from app import models  # noqa: F401 - imports models to register them

settings = get_settings()

# Frontend build directory - check multiple locations for flexibility
_possible_frontend_dirs = [
    Path(__file__).parent.parent.parent / "frontend" / "dist",  # Local dev
    Path("/app/frontend/dist"),  # Docker
]
FRONTEND_DIR = next((p for p in _possible_frontend_dirs if p.exists()), _possible_frontend_dirs[0])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown events."""
    # Create database tables
    Base.metadata.create_all(bind=engine)

    # Startup
    register_sync_job()
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
app.include_router(scheduler.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# Serve frontend static files (if built)
if FRONTEND_DIR.exists():
    # Serve static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    # Catch-all route for client-side routing - must be last
    @app.get("/{full_path:path}")
    async def serve_frontend(request: Request, full_path: str):
        # Don't serve frontend for API routes
        if full_path.startswith("api/"):
            return {"detail": "Not Found"}

        # Serve index.html for all other routes (React Router handles routing)
        return FileResponse(FRONTEND_DIR / "index.html")
