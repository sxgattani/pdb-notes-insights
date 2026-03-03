import asyncio
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

# MCP raw app (FastMCP's Starlette with lifespan). Set below if MCP is enabled;
# referenced in lifespan() at runtime after module-level init completes.
_mcp_raw_app = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown events."""
    # Create database tables
    Base.metadata.create_all(bind=engine)

    # Start MCP session manager lifespan (initialises anyio task group).
    # FastMCP's streamable_http_app() returns a Starlette app whose lifespan
    # calls session_manager.run(). We drive that lifespan manually here so it
    # shares the running event loop with the rest of the app.
    _mcp_task = None
    _mcp_shutdown_event = None
    _mcp_shutdown_done = None
    if _mcp_raw_app is not None:
        started = asyncio.Event()
        _mcp_shutdown_event = asyncio.Event()
        _mcp_shutdown_done = asyncio.Event()

        async def _run_mcp_lifespan():
            async def recv():
                if not started.is_set():
                    return {"type": "lifespan.startup"}
                await _mcp_shutdown_event.wait()
                return {"type": "lifespan.shutdown"}

            async def send(msg):
                if msg["type"] == "lifespan.startup.complete":
                    started.set()
                elif msg["type"] == "lifespan.shutdown.complete":
                    _mcp_shutdown_done.set()

            scope = {"type": "lifespan", "asgi": {"version": "3.0", "spec_version": "2.0"}}
            await _mcp_raw_app(scope, recv, send)

        _mcp_task = asyncio.create_task(_run_mcp_lifespan())
        try:
            await asyncio.wait_for(started.wait(), timeout=15.0)
        except asyncio.TimeoutError:
            _mcp_task.cancel()
            raise RuntimeError("MCP server failed to start within 15 s")

    # App startup
    register_sync_job()
    start_scheduler()

    yield

    # App shutdown
    shutdown_scheduler()

    if _mcp_task is not None:
        _mcp_shutdown_event.set()
        try:
            await asyncio.wait_for(_mcp_shutdown_done.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            pass
        _mcp_task.cancel()
        try:
            await _mcp_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="ProductBoard Insights",
    description="Read-only reporting system for ProductBoard notes",
    version="0.1.0",
    lifespan=lifespan,
)

# Get allowed origins from environment or use defaults
cors_origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://notes-hq.fly.dev",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Set-Cookie"],
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


# Route /mcp paths via ASGI middleware (bypasses FastAPI routing) and start
# the MCP session manager's lifespan from within our own lifespan above.
if settings.mcp_api_key:
    from notes_mcp.server import create_mcp_components
    _mcp_raw_app, _MCPMiddleware = create_mcp_components(api_key=settings.mcp_api_key)
    app.add_middleware(_MCPMiddleware)


# Serve frontend static files (if built)
if FRONTEND_DIR.exists():
    # Serve static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

    # Catch-all route for client-side routing - must be last
    @app.get("/{full_path:path}")
    async def serve_frontend(request: Request, full_path: str):
        # Return 404 for API and well-known discovery paths (not React routes)
        if full_path.startswith("api/") or full_path.startswith(".well-known/"):
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "Not Found"}, status_code=404)

        # Serve index.html for all other routes (React Router handles routing)
        return FileResponse(FRONTEND_DIR / "index.html")
