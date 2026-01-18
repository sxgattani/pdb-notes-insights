from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.scheduler import get_scheduler

router = APIRouter(prefix="/scheduler", tags=["scheduler"])


@router.get("/status")
def get_scheduler_status():
    """Get scheduler status and job information."""
    scheduler = get_scheduler()

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        })

    return {
        "running": scheduler.running,
        "jobs": jobs,
    }


@router.post("/jobs/{job_id}/run")
def run_job_now(job_id: str):
    """Manually trigger a job to run immediately."""
    scheduler = get_scheduler()
    job = scheduler.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    # Modify next run time to now to trigger immediate execution
    job.modify(next_run_time=datetime.utcnow())

    return {
        "message": f"Job '{job_id}' scheduled to run immediately",
        "job_id": job_id,
    }
