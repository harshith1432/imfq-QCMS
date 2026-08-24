"""
Periodic Scheduled Maintenance Tasks (Celery Beat)
=================================================
Automated housekeeping for database health, session lifecycle, and analytics rollup.
"""
import logging
from datetime import datetime, timezone, timedelta
from celery import shared_task
from app.infrastructure.database.models.models import (
    SaaSUserSession, Organization, User, Project, db
)

logger = logging.getLogger("QCMS.Maintenance")


@shared_task(name="app.infrastructure.tasks.maintenance_tasks.cleanup_expired_sessions_and_tokens")
def cleanup_expired_sessions_and_tokens():
    """Purges expired user sessions older than 30 days from database."""
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
    try:
        deleted = SaaSUserSession.query.filter(
            (SaaSUserSession.is_active == False) & (SaaSUserSession.login_time < cutoff)
        ).delete()
        db.session.commit()
        logger.info(f"[Maintenance] Purged {deleted} stale session records.")
        return {"deleted_sessions": deleted}
    except Exception as e:
        db.session.rollback()
        logger.error(f"[Maintenance] Error purging expired sessions: {e}")
        return {"status": "error", "error": str(e)}


@shared_task(name="app.infrastructure.tasks.maintenance_tasks.cleanup_soft_deleted_tenants")
def cleanup_soft_deleted_tenants():
    """Permanently deletes organizations soft-deleted more than 30 days ago."""
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)
    try:
        tenants = Organization.query.filter(
            Organization.is_deleted == True,
            Organization.deleted_at < cutoff
        ).all()
        
        count = len(tenants)
        for t in tenants:
            db.session.delete(t)
        db.session.commit()
        logger.info(f"[Maintenance] Permanently purged {count} soft-deleted organizations.")
        return {"purged_tenants": count}
    except Exception as e:
        db.session.rollback()
        logger.error(f"[Maintenance] Error cleaning soft-deleted tenants: {e}")
        return {"status": "error", "error": str(e)}


@shared_task(name="app.infrastructure.tasks.maintenance_tasks.aggregate_daily_analytics")
def aggregate_daily_analytics():
    """Daily metrics aggregation rollup."""
    try:
        total_orgs = Organization.query.filter_by(is_deleted=False).count()
        total_users = User.query.filter_by(is_active=True).count()
        total_projects = Project.query.count()
        logger.info(f"[Maintenance] Daily rollup: {total_orgs} orgs, {total_users} active users, {total_projects} projects.")
        return {"orgs": total_orgs, "users": total_users, "projects": total_projects}
    except Exception as e:
        logger.error(f"[Maintenance] Error aggregating analytics: {e}")
        return {"status": "error", "error": str(e)}
