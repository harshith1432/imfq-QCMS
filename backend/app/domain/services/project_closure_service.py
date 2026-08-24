"""
Project Closure & Lifecycle Application Service
================================================
Encapsulates all business logic for project closure, reviewer sign-offs,
stage resets, knowledge repository auto-archiving, gamification points,
in-app notifications, and audit logging.
"""
from datetime import datetime, timezone
import logging
from app.infrastructure.database.models import (
    db, Project, User, ProjectStageTracker, ProjectReview,
    Stage8StandardizationKnowledgeSharingProjectClosure, AuditLog
)

logger = logging.getLogger("QCMS.ProjectClosureService")


class ProjectClosureService:
    @staticmethod
    def execute_closure(project_id: int, user_id: int, comments: str = "Reviewer signed off. Project closed.", sign_off_by_role: str = "Reviewer") -> dict:
        """
        Executes complete project closure business logic:
        1. Validates project & user existence.
        2. Sets project status to 'Closed' and records end_date.
        3. Updates Stage 8 sign-offs and stage tracker.
        4. Auto-archives completed project into the Knowledge Repository.
        5. Awards gamification points to all project participants.
        6. Dispatches in-app notifications and background congratulatory emails.
        7. Writes tamper-evident audit log.
        """
        user = db.session.get(User, user_id)
        if not user:
            raise ValueError("User not found")

        project = db.session.get(Project, project_id)
        if not project:
            raise ValueError("Project not found")

        if user.role and user.role.name != 'SuperAdmin' and project.org_id != user.org_id:
            raise PermissionError("Unauthorized access to project")

        # 1. Update Project Status
        project.status = 'Closed'
        project.end_date = datetime.now(timezone.utc).replace(tzinfo=None).date()

        # 2. Stage 8 Sign-offs
        s8 = Stage8StandardizationKnowledgeSharingProjectClosure.query.filter_by(project_id=project_id).first()
        if not s8:
            s8 = Stage8StandardizationKnowledgeSharingProjectClosure(project_id=project_id, org_id=project.org_id)
            db.session.add(s8)

        s8.facilitator_validation = True
        s8.admin_closure = True
        s8.final_approval = True
        s8.final_approval_by = user.id
        s8.final_approval_at = datetime.now(timezone.utc).replace(tzinfo=None)
        s8.final_comments = comments

        # 3. Mark Stage 8 Tracker Completed
        tracker = ProjectStageTracker.query.filter_by(project_id=project_id, stage_number=8).first()
        if tracker:
            tracker.status = 'Completed'
            tracker.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)

        db.session.flush()

        # 4. Auto-archive to Knowledge Repository
        try:
            from app.presentation.routes.repository_routes import auto_archive_project_to_repository
            auto_archive_project_to_repository(project_id, project.org_id)
        except Exception as archive_err:
            logger.warning(f"[ProjectClosureService] Auto-archiving failed: {archive_err}")

        # 5. Award Gamification / Employee Points
        try:
            from app.domain.services.point_engine_service import PointEngineService
            if project.team_leader_id:
                PointEngineService.award_points(
                    employee_id=project.team_leader_id,
                    org_id=project.org_id,
                    activity_type="project_completed",
                    points=100,
                    ref_id=f"PRJ_LEAD_{project.id}",
                    description=f"Led project '{project.title}' to successful closure."
                )
            for m in getattr(project, 'members', []):
                if m.id != project.team_leader_id:
                    PointEngineService.award_points(
                        employee_id=m.id,
                        org_id=project.org_id,
                        activity_type="project_completed",
                        points=50,
                        ref_id=f"PRJ_MEM_{project.id}_{m.id}",
                        description=f"Participated in project '{project.title}' closure."
                    )
        except Exception as pts_err:
            logger.warning(f"[ProjectClosureService] Points awarding notice: {pts_err}")

        # 6. In-App Notifications
        try:
            from app.presentation.routes.notification_routes import create_notification
            notify_ids = {uid for uid in [project.team_leader_id, project.creator_id, project.facilitator_id] if uid and uid != user.id}
            for uid in notify_ids:
                create_notification(
                    project.org_id, uid,
                    "Project Officially Closed",
                    f"{sign_off_by_role} signed off and closed project '{project.title}'.",
                    f"/projects/project-details.html?id={project_id}",
                    commit=False
                )
        except Exception as notif_err:
            logger.warning(f"[ProjectClosureService] In-app notification error: {notif_err}")

        # 7. Audit Log
        db.session.add(AuditLog(
            org_id=project.org_id,
            user_id=user.id,
            project_id=project.id,
            action=f"PROJECT_CLOSED_BY_{sign_off_by_role.upper()}",
            target_table="projects",
            target_id=project.id,
            details={"title": project.title, "comments": comments}
        ))

        db.session.commit()

        # 8. Dispatch Background Congratulatory Email (Non-blocking Thread)
        try:
            import threading
            from flask import current_app
            try:
                app_obj = current_app._get_current_object()
            except Exception:
                app_obj = None
            
            def _async_email(app_instance, pid):
                try:
                    if app_instance:
                        with app_instance.app_context():
                            from app.domain.services.email_notification_engine import EmailNotificationEngine
                            EmailNotificationEngine.trigger_project_completed_notification(pid)
                    else:
                        from app.domain.services.email_notification_engine import EmailNotificationEngine
                        EmailNotificationEngine.trigger_project_completed_notification(pid)
                except Exception as em_err:
                    logger.warning(f"[ProjectClosureService Async Email] {em_err}")

            t = threading.Thread(target=_async_email, args=(app_obj, project.id))
            t.daemon = True
            t.start()
        except Exception as email_err:
            logger.warning(f"[ProjectClosureService] Non-blocking email dispatch notice: {email_err}")

        return {
            "status": "success",
            "message": f"Project '{project.title}' has been officially closed and archived.",
            "project_id": project.id,
            "closed": True
        }

    @staticmethod
    def reject_closure(project_id: int, user_id: int, comments: str = "Rejected by Admin. Please revise.") -> dict:
        """
        Rejects project closure, resets progress back to Stage 1,
        and alerts all project stakeholders.
        """
        user = db.session.get(User, user_id)
        if not user:
            raise ValueError("User not found")

        project = db.session.get(Project, project_id)
        if not project:
            raise ValueError("Project not found")

        if project.status == 'Closed':
            raise ValueError("Cannot reject an already closed project")

        project.status = 'Rejected'
        project.current_stage = 1

        # Reset Stage Trackers
        for tracker in getattr(project, 'stage_tracker', []):
            if tracker.stage_number == 1:
                tracker.status = 'In Progress'
                tracker.completed_at = None
            else:
                tracker.status = 'Pending'
                tracker.started_at = None
                tracker.completed_at = None

        # Reset Stage 8 sign-offs
        s8 = Stage8StandardizationKnowledgeSharingProjectClosure.query.filter_by(project_id=project_id).first()
        if s8:
            s8.facilitator_validation = False
            s8.admin_closure = False
            s8.final_approval = False
            s8.final_comments = f"Rejected. Comments: {comments}"

        # Record rejection review
        review = ProjectReview(
            org_id=project.org_id,
            project_id=project.id,
            stage_number=8,
            reviewer_id=user.id,
            status='Approved',
            decision='Rejected',
            comments=comments,
            decided_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        db.session.add(review)

        # Notify team
        try:
            from app.presentation.routes.notification_routes import create_notification
            notify_ids = {uid for uid in [project.team_leader_id, project.facilitator_id, project.reviewer_id, project.creator_id] if uid and uid != user.id}
            for uid in notify_ids:
                create_notification(
                    project.org_id, uid,
                    "Project Rejected & Reset",
                    f"Closure rejected for '{project.title}': {comments}",
                    f"/projects/project-details.html?id={project_id}",
                    commit=False
                )
        except Exception as notif_err:
            logger.warning(f"[ProjectClosureService] In-app notification notice: {notif_err}")

        # Audit Log
        db.session.add(AuditLog(
            org_id=project.org_id,
            user_id=user.id,
            project_id=project.id,
            action="PROJECT_CLOSURE_REJECTED",
            target_table="projects",
            target_id=project.id,
            details={"title": project.title, "comments": comments}
        ))

        db.session.commit()

        return {
            "status": "success",
            "message": "Project rejected and reset to Stage 1 successfully.",
            "project_id": project.id
        }
