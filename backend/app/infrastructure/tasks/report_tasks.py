"""
Asynchronous PDF & Excel Generation Tasks
========================================
Processes resource-heavy reports off the HTTP thread pool.
"""
import logging
from datetime import datetime, timezone
from celery import shared_task
from app.infrastructure.database.models.models import Project, KPIMetric, AuditLog, User, db
from app.infrastructure.storage import storage

logger = logging.getLogger("QCMS.Reports")


@shared_task(bind=True, name="app.infrastructure.tasks.report_tasks.generate_async_pdf_report")
def generate_async_pdf_report(self, project_id: int, tool_name: str = None, user_id: int = None, org_id: int = None):
    """Generates an 8D or QC Tool PDF report asynchronously with status updates."""
    logger.info(f"[Celery PDF Task] Starting report for project {project_id} (tool={tool_name})")
    
    self.update_state(state="PROGRESS", meta={"progress": 20, "status": "Locating project records"})
    
    project = db.session.get(Project, project_id)
    if not project:
        logger.error(f"[Celery PDF Task] Project {project_id} not found")
        return {"status": "failed", "error": "Project not found"}

    self.update_state(state="PROGRESS", meta={"progress": 50, "status": "Compiling PDF story sections"})
    
    pdf_data = None
    filename = f"{project.project_uid}_QC_Story_Report.pdf"

    if tool_name:
        from app.utils.report_gen import generate_qc_tool_report
        pdf_data = generate_qc_tool_report(project.id, tool_name)
        filename = f"{project.project_uid}_{tool_name}_report.pdf"
    else:
        from app.utils.pdf_filler import generate_qc_story_closure_summary_pdf
        try:
            pdf_data = generate_qc_story_closure_summary_pdf(project.id)
        except Exception as e:
            logger.warning(f"[Celery PDF Task] Primary filler error: {e}")

        if not pdf_data:
            from app.utils.report_gen import generate_pdf_summary
            kpi = KPIMetric.query.filter_by(project_id=project.id).first()
            pdf_out = generate_pdf_summary(project, kpi, project.org_id)
            if pdf_out:
                pdf_data = pdf_out.encode('latin-1') if isinstance(pdf_out, str) else bytes(pdf_out)

    if not pdf_data:
        logger.error(f"[Celery PDF Task] Failed to produce PDF data for project {project_id}")
        return {"status": "failed", "error": "Could not generate PDF document"}

    self.update_state(state="PROGRESS", meta={"progress": 80, "status": "Saving document to cloud storage"})
    
    saved = storage.save_file(
        pdf_data,
        filename=filename,
        subfolder="reports",
        content_type="application/pdf"
    )

    download_url = saved.get("url")
    
    # Audit log entry
    if user_id and org_id:
        try:
            db.session.add(AuditLog(
                org_id=org_id,
                user_id=user_id,
                project_id=project.id,
                action=f"ASYNC_EXPORT_PDF_{tool_name.upper()}" if tool_name else "ASYNC_EXPORT_PDF_8D",
                target_table="projects",
                target_id=project.id,
                details={"task_id": self.request.id, "url": download_url}
            ))
            db.session.commit()
        except Exception as aud_err:
            logger.warning(f"[Celery PDF Task] Audit log commit failed: {aud_err}")

    logger.info(f"[Celery PDF Task] Completed report for project {project_id} -> {download_url}")
    return {
        "status": "completed",
        "progress": 100,
        "filename": filename,
        "download_url": download_url,
        "completed_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    }


@shared_task(bind=True, name="app.infrastructure.tasks.report_tasks.generate_async_excel_export")
def generate_async_excel_export(self, user_id: int, org_id: int):
    """Generates a complete organization-wide Excel report in the background."""
    self.update_state(state="PROGRESS", meta={"progress": 25, "status": "Fetching organization projects"})
    
    user = db.session.get(User, user_id)
    if not user:
        return {"status": "failed", "error": "User context not found"}

    from app.presentation.routes.reports_routes import _get_user_projects
    from app.utils.report_gen import generate_excel_report
    
    projects = _get_user_projects(user).all()
    
    self.update_state(state="PROGRESS", meta={"progress": 60, "status": "Building multi-sheet Excel workbook"})
    excel_file = generate_excel_report(projects)
    excel_bytes = excel_file.getvalue() if hasattr(excel_file, 'getvalue') else excel_file.read()

    filename = f"QCMS_Projects_Export_{datetime.now(timezone.utc).replace(tzinfo=None).strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    saved = storage.save_file(
        excel_bytes,
        filename=filename,
        subfolder="exports",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    return {
        "status": "completed",
        "progress": 100,
        "filename": filename,
        "download_url": saved.get("url"),
        "completed_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    }


@shared_task(bind=True, name="app.infrastructure.tasks.report_tasks.generate_async_bulk_pdf_zip")
def generate_async_bulk_pdf_zip(self, user_id: int, org_id: int, is_super_admin: bool = False):
    """Generates a zip archive containing PDFs of all closed projects asynchronously."""
    import io
    import zipfile
    from app.infrastructure.database.models.models import Project, KPIMetric, AuditLog, User, db
    from app.infrastructure.storage import storage
    from app.utils.pdf_filler import generate_qc_story_closure_summary_pdf
    from app.utils.report_gen import generate_pdf_summary

    self.update_state(state="PROGRESS", meta={"progress": 10, "status": "Locating closed projects"})
    
    closed_statuses = ('Closed', 'Completed', 'Archived', 'Stage 8 Approved', 'Stage 8 Submitted', 'Pending Closure', 'SOP Created')
    if is_super_admin:
        projects = Project.query.filter(Project.status.in_(closed_statuses)).all()
    else:
        from app.presentation.routes.reports_routes import _get_user_projects
        user = db.session.get(User, user_id)
        if not user:
            return {"status": "failed", "error": "User not found"}
        projects = _get_user_projects(user).filter(Project.status.in_(closed_statuses)).all()

    if not projects:
        return {"status": "failed", "error": "No closed projects found"}

    total_projects = len(projects)
    zip_buffer = io.BytesIO()
    success_count = 0

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for idx, p in enumerate(projects):
            progress = 10 + int((idx / total_projects) * 80)
            self.update_state(state="PROGRESS", meta={
                "progress": progress,
                "status": f"Generating PDF {idx + 1} of {total_projects} ({p.project_uid})"
            })
            try:
                pdf_data = generate_qc_story_closure_summary_pdf(p.id)
                if not pdf_data:
                    kpi = KPIMetric.query.filter_by(project_id=p.id).first()
                    pdf_out = generate_pdf_summary(p, kpi, p.org_id)
                    if pdf_out:
                        pdf_data = pdf_out.encode('latin-1') if isinstance(pdf_out, str) else bytes(pdf_out)

                if pdf_data:
                    safe_uid = (p.project_uid or f'PRJ_{p.id}').replace('/', '_')
                    zf.writestr(f"{safe_uid}_QC_Story_Report.pdf", pdf_data)
                    success_count += 1
            except Exception as e:
                logger.warning(f"[Bulk PDF Task] Failed for project {p.id}: {e}")

    if success_count == 0:
        return {"status": "failed", "error": "No PDFs could be generated"}

    self.update_state(state="PROGRESS", meta={"progress": 95, "status": "Saving ZIP archive to storage"})
    
    zip_buffer.seek(0)
    filename = f"QCMS_All_Project_Reports_{org_id or 'all'}.zip"
    saved = storage.save_file(
        zip_buffer.getvalue(),
        filename=filename,
        subfolder="reports/bulk",
        content_type="application/zip"
    )
    download_url = saved.get("url")

    # Log audit event
    try:
        db.session.add(AuditLog(
            org_id=org_id,
            user_id=user_id,
            action="ASYNC_EXPORT_PDF_ALL",
            target_table="projects",
            details={"count": success_count, "task_id": self.request.id, "url": download_url}
        ))
        db.session.commit()
    except Exception:
        pass

    return {
        "status": "completed",
        "progress": 100,
        "filename": filename,
        "download_url": download_url,
        "count": success_count,
        "completed_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    }
