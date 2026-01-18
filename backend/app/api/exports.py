from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Literal

from app.database import get_db
from app.models import Export
from app.services.exports import JSONExportService, PDFExportService

router = APIRouter(prefix="/exports", tags=["exports"])


class ExportRequest(BaseModel):
    report_type: Literal["notes_summary", "features_summary", "pm_performance", "sla_report"]
    format: Literal["pdf", "json"]


def _generate_export(export_id: int, report_type: str, format: str, db: Session):
    """Background task to generate the export file."""
    # Get fresh db session for background task
    from app.database import SessionLocal
    db = SessionLocal()

    try:
        # Get the export record
        export = db.query(Export).filter(Export.id == export_id).first()
        if not export:
            return

        # Select the appropriate service based on format
        if format == "json":
            service = JSONExportService(db)
        else:
            service = PDFExportService(db)

        # Delete the pending export record since service will create its own
        db.delete(export)
        db.commit()

        # Generate the report based on type
        if report_type == "notes_summary":
            service.generate_notes_summary(triggered_by="manual")
        elif report_type == "features_summary":
            service.generate_features_summary(triggered_by="manual")
        elif report_type == "pm_performance":
            service.generate_pm_performance(triggered_by="manual")
        elif report_type == "sla_report":
            service.generate_sla_report(triggered_by="manual")
    finally:
        db.close()


@router.post("")
def trigger_export(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Trigger a new export. Returns immediately with export ID."""
    # Create a pending export record
    export = Export(
        report_type=request.report_type,
        format=request.format,
        filename="",  # Will be set when generation completes
        file_path="",  # Will be set when generation completes
        status="pending",
        triggered_by="manual",
    )
    db.add(export)
    db.commit()
    db.refresh(export)

    # Add background task to generate the export
    background_tasks.add_task(
        _generate_export,
        export.id,
        request.report_type,
        request.format,
        db
    )

    return {
        "id": export.id,
        "status": "pending",
        "message": f"Export '{request.report_type}' in {request.format} format has been queued"
    }


@router.get("")
def list_exports(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List past exports with pagination."""
    # Get total count
    total = db.query(Export).count()

    # Query exports ordered by created_at desc
    exports = (
        db.query(Export)
        .order_by(Export.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "data": [
            {
                "id": export.id,
                "report_type": export.report_type,
                "format": export.format,
                "filename": export.filename,
                "file_size": export.file_size,
                "status": export.status,
                "error_message": export.error_message,
                "created_at": export.created_at.isoformat() if export.created_at else None,
                "completed_at": export.completed_at.isoformat() if export.completed_at else None,
                "triggered_by": export.triggered_by,
            }
            for export in exports
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{export_id}")
def get_export(export_id: int, db: Session = Depends(get_db)):
    """Get export details."""
    export = db.query(Export).filter(Export.id == export_id).first()

    if not export:
        raise HTTPException(status_code=404, detail="Export not found")

    return {
        "id": export.id,
        "report_type": export.report_type,
        "format": export.format,
        "filename": export.filename,
        "file_path": export.file_path,
        "file_size": export.file_size,
        "status": export.status,
        "error_message": export.error_message,
        "created_at": export.created_at.isoformat() if export.created_at else None,
        "completed_at": export.completed_at.isoformat() if export.completed_at else None,
        "triggered_by": export.triggered_by,
    }


@router.get("/{export_id}/download")
def download_export(export_id: int, db: Session = Depends(get_db)):
    """Download the export file."""
    export = db.query(Export).filter(Export.id == export_id).first()

    if not export:
        raise HTTPException(status_code=404, detail="Export not found")

    if export.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Export is not ready for download. Current status: {export.status}"
        )

    # Check if file exists
    file_path = Path(export.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Export file not found on disk")

    # Determine media type based on format
    if export.format == "pdf":
        media_type = "application/pdf"
    else:
        media_type = "application/json"

    return FileResponse(
        path=str(file_path),
        filename=export.filename,
        media_type=media_type,
    )
