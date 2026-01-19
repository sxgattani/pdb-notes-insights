from datetime import datetime, timedelta
from pathlib import Path
import json
from sqlalchemy.orm import Session
from sqlalchemy import func, Integer

from app.config import get_settings
from app.models import Note, Feature, Member, Export

SLA_DAYS = 5  # Notes should be processed within 5 days


class JSONExportService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def _ensure_export_dir(self) -> Path:
        """Ensure export directory exists."""
        export_dir = Path(self.settings.export_path)
        date_dir = export_dir / datetime.utcnow().strftime("%Y-%m-%d")
        date_dir.mkdir(parents=True, exist_ok=True)
        return date_dir

    def _save_json(self, data: dict, filename: str) -> tuple[str, int]:
        """Save data to JSON file, return (path, size)."""
        export_dir = self._ensure_export_dir()
        file_path = export_dir / filename
        content = json.dumps(data, indent=2, default=str)
        file_path.write_text(content)
        return str(file_path), len(content)

    def _create_export_record(
        self, report_type: str, filename: str, triggered_by: str
    ) -> Export:
        """Create an export record with status='generating'."""
        export = Export(
            report_type=report_type,
            format="json",
            filename=filename,
            file_path="",  # Will be updated after file is saved
            status="generating",
            triggered_by=triggered_by,
        )
        self.db.add(export)
        self.db.commit()
        self.db.refresh(export)
        return export

    def _complete_export(
        self, export: Export, file_path: str, file_size: int
    ) -> Export:
        """Update export record to completed status."""
        export.file_path = file_path
        export.file_size = file_size
        export.status = "completed"
        export.completed_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(export)
        return export

    def _fail_export(self, export: Export, error_message: str) -> Export:
        """Update export record to failed status."""
        export.status = "failed"
        export.error_message = error_message
        self.db.commit()
        self.db.refresh(export)
        return export

    def generate_notes_summary(self, triggered_by: str = "manual") -> Export:
        """Generate notes summary JSON export."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"notes_summary_{timestamp}.json"

        # Create export record
        export = self._create_export_record("notes_summary", filename, triggered_by)

        try:
            # Query notes stats
            total_notes = self.db.query(func.count(Note.id)).scalar() or 0
            unprocessed_notes = (
                self.db.query(func.count(Note.id))
                .filter(Note.state == "unprocessed")
                .scalar()
                or 0
            )
            processed_notes = (
                self.db.query(func.count(Note.id))
                .filter(Note.state == "processed")
                .scalar()
                or 0
            )

            # Notes by source origin
            notes_by_source = dict(
                self.db.query(Note.source_origin, func.count(Note.id))
                .group_by(Note.source_origin)
                .all()
            )

            # Recent notes (last 7 days)
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_notes_count = (
                self.db.query(func.count(Note.id))
                .filter(Note.created_at >= week_ago)
                .scalar()
                or 0
            )

            data = {
                "report": "notes_summary",
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "data": {
                    "total_notes": total_notes,
                    "unprocessed_notes": unprocessed_notes,
                    "processed_notes": processed_notes,
                    "processing_rate": round(
                        processed_notes / max(total_notes, 1) * 100, 1
                    ),
                    "notes_by_source": notes_by_source,
                    "recent_notes_7d": recent_notes_count,
                },
            }

            file_path, file_size = self._save_json(data, filename)
            return self._complete_export(export, file_path, file_size)

        except Exception as e:
            return self._fail_export(export, str(e))

    def generate_features_summary(self, triggered_by: str = "manual") -> Export:
        """Generate features summary JSON export."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"features_summary_{timestamp}.json"

        # Create export record
        export = self._create_export_record("features_summary", filename, triggered_by)

        try:
            # Query features stats
            total_features = self.db.query(func.count(Feature.id)).scalar() or 0

            # Features by type
            features_by_type = dict(
                self.db.query(Feature.type, func.count(Feature.id))
                .group_by(Feature.type)
                .all()
            )

            # Features by status
            features_by_status = dict(
                self.db.query(Feature.status, func.count(Feature.id))
                .group_by(Feature.status)
                .all()
            )

            # Features by product area
            features_by_product_area = dict(
                self.db.query(Feature.product_area, func.count(Feature.id))
                .group_by(Feature.product_area)
                .all()
            )

            # Committed features count
            committed_count = (
                self.db.query(func.count(Feature.id))
                .filter(Feature.committed == True)
                .scalar()
                or 0
            )

            # Features by risk
            features_by_risk = dict(
                self.db.query(Feature.risk, func.count(Feature.id))
                .group_by(Feature.risk)
                .all()
            )

            data = {
                "report": "features_summary",
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "data": {
                    "total_features": total_features,
                    "committed_features": committed_count,
                    "commitment_rate": round(
                        committed_count / max(total_features, 1) * 100, 1
                    ),
                    "features_by_type": features_by_type,
                    "features_by_status": features_by_status,
                    "features_by_product_area": features_by_product_area,
                    "features_by_risk": features_by_risk,
                },
            }

            file_path, file_size = self._save_json(data, filename)
            return self._complete_export(export, file_path, file_size)

        except Exception as e:
            return self._fail_export(export, str(e))

    def generate_pm_performance(self, triggered_by: str = "manual") -> Export:
        """Generate PM performance JSON export."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"pm_performance_{timestamp}.json"

        # Create export record
        export = self._create_export_record("pm_performance", filename, triggered_by)

        try:
            # Get note counts per owner
            note_stats = (
                self.db.query(
                    Member.id,
                    Member.name,
                    Member.email,
                    func.count(Note.id).label("total_notes"),
                    func.sum(func.cast(Note.state == "unprocessed", Integer)).label(
                        "unprocessed_notes"
                    ),
                    func.sum(func.cast(Note.state == "processed", Integer)).label(
                        "processed_notes"
                    ),
                )
                .outerjoin(Note, Note.owner_id == Member.id)
                .group_by(Member.id, Member.name, Member.email)
                .all()
            )

            # Get feature counts per owner
            feature_counts = dict(
                self.db.query(Feature.owner_id, func.count(Feature.id))
                .group_by(Feature.owner_id)
                .all()
            )

            pm_data = []
            for user_id, name, email, total_notes, unprocessed, processed in note_stats:
                total_notes = total_notes or 0
                unprocessed = unprocessed or 0
                processed = processed or 0
                features = feature_counts.get(user_id, 0)

                pm_data.append(
                    {
                        "user_id": user_id,
                        "name": name or email or "Unknown",
                        "email": email,
                        "total_notes": total_notes,
                        "unprocessed_notes": unprocessed,
                        "processed_notes": processed,
                        "processing_rate": round(
                            processed / max(total_notes, 1) * 100, 1
                        ),
                        "total_features": features,
                    }
                )

            # Sort by processing rate descending (best performers first)
            pm_data.sort(key=lambda x: x["processing_rate"], reverse=True)

            data = {
                "report": "pm_performance",
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "data": {
                    "pm_metrics": pm_data,
                    "summary": {
                        "total_pms": len(pm_data),
                        "total_notes": sum(p["total_notes"] for p in pm_data),
                        "total_unprocessed": sum(p["unprocessed_notes"] for p in pm_data),
                        "total_processed": sum(p["processed_notes"] for p in pm_data),
                        "total_features": sum(p["total_features"] for p in pm_data),
                    },
                },
            }

            file_path, file_size = self._save_json(data, filename)
            return self._complete_export(export, file_path, file_size)

        except Exception as e:
            return self._fail_export(export, str(e))

    def generate_sla_report(self, triggered_by: str = "manual") -> Export:
        """Generate SLA compliance JSON export."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"sla_report_{timestamp}.json"

        # Create export record
        export = self._create_export_record("sla_report", filename, triggered_by)

        try:
            now = datetime.utcnow()
            sla_threshold = now - timedelta(days=SLA_DAYS)
            warning_threshold = now - timedelta(days=SLA_DAYS - 1)

            # Get all unprocessed notes
            unprocessed_notes = (
                self.db.query(Note).filter(Note.state == "unprocessed").all()
            )

            at_risk = []
            breached = []
            on_track = []

            for note in unprocessed_notes:
                if not note.created_at:
                    continue

                note_data = {
                    "id": note.id,
                    "title": note.title,
                    "created_at": note.created_at.isoformat(),
                    "days_old": (now - note.created_at).days,
                    "owner_id": note.owner_id,
                }

                if note.created_at < sla_threshold:
                    breached.append(note_data)
                elif note.created_at < warning_threshold:
                    at_risk.append(note_data)
                else:
                    on_track.append(note_data)

            # Sort by age (oldest first for breached/at_risk)
            breached.sort(key=lambda x: x["days_old"], reverse=True)
            at_risk.sort(key=lambda x: x["days_old"], reverse=True)

            total_unprocessed = len(unprocessed_notes)

            # SLA by owner
            breached_by_owner = (
                self.db.query(
                    Member.id,
                    Member.name,
                    Member.email,
                    func.count(Note.id).label("breached_count"),
                )
                .join(Note, Note.owner_id == Member.id)
                .filter(Note.state == "unprocessed")
                .filter(Note.created_at < sla_threshold)
                .group_by(Member.id, Member.name, Member.email)
                .all()
            )

            sla_by_owner = [
                {
                    "user_id": user_id,
                    "name": name or email or "Unknown",
                    "breached_count": breached_count,
                }
                for user_id, name, email, breached_count in breached_by_owner
            ]
            sla_by_owner.sort(key=lambda x: x["breached_count"], reverse=True)

            data = {
                "report": "sla_report",
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "data": {
                    "summary": {
                        "total_unprocessed": total_unprocessed,
                        "breached": len(breached),
                        "at_risk": len(at_risk),
                        "on_track": len(on_track),
                        "sla_compliance_rate": round(
                            (1 - len(breached) / max(total_unprocessed, 1)) * 100, 1
                        ),
                        "sla_days": SLA_DAYS,
                    },
                    "breached_notes": breached,
                    "at_risk_notes": at_risk,
                    "sla_by_owner": sla_by_owner,
                },
            }

            file_path, file_size = self._save_json(data, filename)
            return self._complete_export(export, file_path, file_size)

        except Exception as e:
            return self._fail_export(export, str(e))
