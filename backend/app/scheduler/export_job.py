import logging
from datetime import datetime

from app.database import SessionLocal
from app.config import get_settings
from app.services.exports import JSONExportService, PDFExportService
from app.scheduler import get_scheduler

logger = logging.getLogger(__name__)


def run_export_job():
    """Run the nightly export job - generates all reports in both formats."""
    logger.info(f"Starting scheduled exports at {datetime.utcnow().isoformat()}")

    db = SessionLocal()
    try:
        json_service = JSONExportService(db)
        pdf_service = PDFExportService(db)

        reports = ['notes_summary', 'features_summary', 'pm_performance', 'sla_report']
        results = {'json': [], 'pdf': []}

        for report_type in reports:
            # Generate JSON
            try:
                method = getattr(json_service, f'generate_{report_type}')
                export = method(triggered_by='scheduler')
                results['json'].append({'report': report_type, 'status': export.status})
            except Exception as e:
                logger.error(f"Failed to generate JSON {report_type}: {e}")
                results['json'].append({'report': report_type, 'status': 'failed'})

            # Generate PDF
            try:
                method = getattr(pdf_service, f'generate_{report_type}')
                export = method(triggered_by='scheduler')
                results['pdf'].append({'report': report_type, 'status': export.status})
            except Exception as e:
                logger.error(f"Failed to generate PDF {report_type}: {e}")
                results['pdf'].append({'report': report_type, 'status': 'failed'})

        logger.info(f"Export job completed: {results}")
        return results

    except Exception as e:
        logger.error(f"Export job failed: {e}")
        raise
    finally:
        db.close()


def register_export_job():
    """Register the export job with the scheduler."""
    settings = get_settings()
    scheduler = get_scheduler()

    # Add cron job - runs at specified hour (default 2 AM)
    scheduler.add_job(
        run_export_job,
        'cron',
        hour=settings.export_schedule_hour,
        minute=0,
        id='nightly_exports',
        name='Nightly Exports',
        replace_existing=True,
    )

    logger.info(f"Export job registered: daily at {settings.export_schedule_hour}:00 UTC")
