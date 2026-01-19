from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import func, Integer
from weasyprint import HTML, CSS

from app.config import get_settings
from app.models import Note, Feature, Member, Export

SLA_DAYS = 5  # Notes should be processed within 5 days


class PDFExportService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def _get_base_css(self) -> str:
        """Return base CSS for all PDF reports."""
        return """
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; border-bottom: 2px solid #333; }
        h2 { color: #666; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f4f4f4; }
        .stat-card { display: inline-block; padding: 20px; margin: 10px; background: #f9f9f9; border-radius: 8px; }
        .stat-value { font-size: 24px; font-weight: bold; color: #333; }
        .stat-label { color: #666; }
        .section { margin: 30px 0; }
        .breached { color: #d32f2f; }
        .at-risk { color: #f57c00; }
        .on-track { color: #388e3c; }
        """

    def _render_html_to_pdf(self, html_content: str, filename: str) -> tuple[str, int]:
        """Render HTML to PDF file, return (path, size)."""
        export_dir = Path(self.settings.export_path) / datetime.utcnow().strftime("%Y-%m-%d")
        export_dir.mkdir(parents=True, exist_ok=True)
        file_path = export_dir / filename

        html = HTML(string=html_content)
        html.write_pdf(str(file_path), stylesheets=[CSS(string=self._get_base_css())])

        return str(file_path), file_path.stat().st_size

    def _create_export_record(
        self, report_type: str, filename: str, triggered_by: str
    ) -> Export:
        """Create an export record with status='generating'."""
        export = Export(
            report_type=report_type,
            format="pdf",
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
        """Generate notes summary PDF."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"notes_summary_{timestamp}.pdf"

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

            processing_rate = round(processed_notes / max(total_notes, 1) * 100, 1)

            # Build HTML
            generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

            # Build notes by source table rows
            source_rows = ""
            for source, count in sorted(notes_by_source.items(), key=lambda x: x[1], reverse=True):
                source_rows += f"<tr><td>{source or 'Unknown'}</td><td>{count}</td></tr>"

            html_content = f"""<!DOCTYPE html>
<html>
<head><title>Notes Summary Report</title></head>
<body>
  <h1>Notes Summary Report</h1>
  <p>Generated: {generated_at}</p>

  <div class="section">
    <h2>Overview</h2>
    <div class="stat-card">
      <div class="stat-value">{total_notes}</div>
      <div class="stat-label">Total Notes</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{processed_notes}</div>
      <div class="stat-label">Processed</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{unprocessed_notes}</div>
      <div class="stat-label">Unprocessed</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{processing_rate}%</div>
      <div class="stat-label">Processing Rate</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{recent_notes_count}</div>
      <div class="stat-label">Last 7 Days</div>
    </div>
  </div>

  <div class="section">
    <h2>Notes by Source</h2>
    <table>
      <tr><th>Source</th><th>Count</th></tr>
      {source_rows}
    </table>
  </div>
</body>
</html>"""

            file_path, file_size = self._render_html_to_pdf(html_content, filename)
            return self._complete_export(export, file_path, file_size)

        except Exception as e:
            return self._fail_export(export, str(e))

    def generate_features_summary(self, triggered_by: str = "manual") -> Export:
        """Generate features summary PDF."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"features_summary_{timestamp}.pdf"

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

            commitment_rate = round(committed_count / max(total_features, 1) * 100, 1)
            generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

            # Build table rows
            type_rows = ""
            for feature_type, count in sorted(features_by_type.items(), key=lambda x: x[1], reverse=True):
                type_rows += f"<tr><td>{feature_type or 'Unknown'}</td><td>{count}</td></tr>"

            status_rows = ""
            for status, count in sorted(features_by_status.items(), key=lambda x: x[1], reverse=True):
                status_rows += f"<tr><td>{status or 'Unknown'}</td><td>{count}</td></tr>"

            product_area_rows = ""
            for area, count in sorted(features_by_product_area.items(), key=lambda x: x[1], reverse=True):
                product_area_rows += f"<tr><td>{area or 'Unknown'}</td><td>{count}</td></tr>"

            risk_rows = ""
            for risk, count in sorted(features_by_risk.items(), key=lambda x: x[1], reverse=True):
                risk_rows += f"<tr><td>{risk or 'Unknown'}</td><td>{count}</td></tr>"

            html_content = f"""<!DOCTYPE html>
<html>
<head><title>Features Summary Report</title></head>
<body>
  <h1>Features Summary Report</h1>
  <p>Generated: {generated_at}</p>

  <div class="section">
    <h2>Overview</h2>
    <div class="stat-card">
      <div class="stat-value">{total_features}</div>
      <div class="stat-label">Total Features</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{committed_count}</div>
      <div class="stat-label">Committed</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{commitment_rate}%</div>
      <div class="stat-label">Commitment Rate</div>
    </div>
  </div>

  <div class="section">
    <h2>Features by Type</h2>
    <table>
      <tr><th>Type</th><th>Count</th></tr>
      {type_rows}
    </table>
  </div>

  <div class="section">
    <h2>Features by Status</h2>
    <table>
      <tr><th>Status</th><th>Count</th></tr>
      {status_rows}
    </table>
  </div>

  <div class="section">
    <h2>Features by Product Area</h2>
    <table>
      <tr><th>Product Area</th><th>Count</th></tr>
      {product_area_rows}
    </table>
  </div>

  <div class="section">
    <h2>Features by Risk</h2>
    <table>
      <tr><th>Risk Level</th><th>Count</th></tr>
      {risk_rows}
    </table>
  </div>
</body>
</html>"""

            file_path, file_size = self._render_html_to_pdf(html_content, filename)
            return self._complete_export(export, file_path, file_size)

        except Exception as e:
            return self._fail_export(export, str(e))

    def generate_pm_performance(self, triggered_by: str = "manual") -> Export:
        """Generate PM performance PDF."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"pm_performance_{timestamp}.pdf"

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

            # Calculate summary
            total_pms = len(pm_data)
            total_notes_sum = sum(p["total_notes"] for p in pm_data)
            total_unprocessed = sum(p["unprocessed_notes"] for p in pm_data)
            total_processed = sum(p["processed_notes"] for p in pm_data)
            total_features = sum(p["total_features"] for p in pm_data)

            generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

            # Build PM table rows
            pm_rows = ""
            for pm in pm_data:
                pm_rows += f"""<tr>
                  <td>{pm['name']}</td>
                  <td>{pm['email'] or 'N/A'}</td>
                  <td>{pm['total_notes']}</td>
                  <td>{pm['processed_notes']}</td>
                  <td>{pm['unprocessed_notes']}</td>
                  <td>{pm['processing_rate']}%</td>
                  <td>{pm['total_features']}</td>
                </tr>"""

            html_content = f"""<!DOCTYPE html>
<html>
<head><title>PM Performance Report</title></head>
<body>
  <h1>PM Performance Report</h1>
  <p>Generated: {generated_at}</p>

  <div class="section">
    <h2>Summary</h2>
    <div class="stat-card">
      <div class="stat-value">{total_pms}</div>
      <div class="stat-label">Total PMs</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{total_notes_sum}</div>
      <div class="stat-label">Total Notes</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{total_processed}</div>
      <div class="stat-label">Processed</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{total_unprocessed}</div>
      <div class="stat-label">Unprocessed</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{total_features}</div>
      <div class="stat-label">Total Features</div>
    </div>
  </div>

  <div class="section">
    <h2>PM Metrics</h2>
    <table>
      <tr>
        <th>Name</th>
        <th>Email</th>
        <th>Total Notes</th>
        <th>Processed</th>
        <th>Unprocessed</th>
        <th>Processing Rate</th>
        <th>Features</th>
      </tr>
      {pm_rows}
    </table>
  </div>
</body>
</html>"""

            file_path, file_size = self._render_html_to_pdf(html_content, filename)
            return self._complete_export(export, file_path, file_size)

        except Exception as e:
            return self._fail_export(export, str(e))

    def generate_sla_report(self, triggered_by: str = "manual") -> Export:
        """Generate SLA report PDF."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"sla_report_{timestamp}.pdf"

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
                    "created_at": note.created_at.strftime("%Y-%m-%d"),
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
            sla_compliance_rate = round(
                (1 - len(breached) / max(total_unprocessed, 1)) * 100, 1
            )

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

            generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

            # Build breached notes table rows
            breached_rows = ""
            for note in breached:
                breached_rows += f"""<tr>
                  <td>{note['id']}</td>
                  <td>{note['title'] or 'Untitled'}</td>
                  <td>{note['created_at']}</td>
                  <td class="breached">{note['days_old']} days</td>
                </tr>"""

            # Build at-risk notes table rows
            at_risk_rows = ""
            for note in at_risk:
                at_risk_rows += f"""<tr>
                  <td>{note['id']}</td>
                  <td>{note['title'] or 'Untitled'}</td>
                  <td>{note['created_at']}</td>
                  <td class="at-risk">{note['days_old']} days</td>
                </tr>"""

            # Build SLA by owner table rows
            owner_rows = ""
            for owner in sla_by_owner:
                owner_rows += f"""<tr>
                  <td>{owner['name']}</td>
                  <td class="breached">{owner['breached_count']}</td>
                </tr>"""

            html_content = f"""<!DOCTYPE html>
<html>
<head><title>SLA Report</title></head>
<body>
  <h1>SLA Report</h1>
  <p>Generated: {generated_at}</p>
  <p>SLA Threshold: {SLA_DAYS} days</p>

  <div class="section">
    <h2>Summary</h2>
    <div class="stat-card">
      <div class="stat-value">{total_unprocessed}</div>
      <div class="stat-label">Total Unprocessed</div>
    </div>
    <div class="stat-card">
      <div class="stat-value breached">{len(breached)}</div>
      <div class="stat-label">Breached</div>
    </div>
    <div class="stat-card">
      <div class="stat-value at-risk">{len(at_risk)}</div>
      <div class="stat-label">At Risk</div>
    </div>
    <div class="stat-card">
      <div class="stat-value on-track">{len(on_track)}</div>
      <div class="stat-label">On Track</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{sla_compliance_rate}%</div>
      <div class="stat-label">SLA Compliance</div>
    </div>
  </div>

  <div class="section">
    <h2>SLA Breaches by Owner</h2>
    <table>
      <tr><th>Owner</th><th>Breached Count</th></tr>
      {owner_rows if owner_rows else '<tr><td colspan="2">No SLA breaches</td></tr>'}
    </table>
  </div>

  <div class="section">
    <h2>Breached Notes (>{SLA_DAYS} days old)</h2>
    <table>
      <tr><th>ID</th><th>Title</th><th>Created</th><th>Age</th></tr>
      {breached_rows if breached_rows else '<tr><td colspan="4">No breached notes</td></tr>'}
    </table>
  </div>

  <div class="section">
    <h2>At-Risk Notes ({SLA_DAYS - 1}-{SLA_DAYS} days old)</h2>
    <table>
      <tr><th>ID</th><th>Title</th><th>Created</th><th>Age</th></tr>
      {at_risk_rows if at_risk_rows else '<tr><td colspan="4">No at-risk notes</td></tr>'}
    </table>
  </div>
</body>
</html>"""

            file_path, file_size = self._render_html_to_pdf(html_content, filename)
            return self._complete_export(export, file_path, file_size)

        except Exception as e:
            return self._fail_export(export, str(e))
