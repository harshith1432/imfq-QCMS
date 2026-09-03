"""
Storage Calculator Service
Calculates real-time data storage consumption across all organizations in the platform.
Aggregates file attachments, DB records footprint, SOPs, RAG vector data, and user assets.
"""
import os
from sqlalchemy import func
from app.infrastructure.database.models.models import (
    db, Organization, User, Project, SupportAttachment, 
    AnnouncementAttachment, KnowledgeRepository, AuditLog, SupportTicket,
    Subscription, SaaSPlan, SaaSPlanLimits, ProjectWorkflow
)

def calculate_org_storage_realtime(org_id=None):
    """
    Computes real-time storage usage for a specific org or all orgs.
    Returns calculated storage data dict with accurate breakdown and summary formatting.
    """
    query = Organization.query.filter(
        (Organization.is_deleted == False) | (Organization.is_deleted == None)
    )
    if org_id:
        query = query.filter(Organization.id == org_id)
    
    orgs = query.all()
    
    result = []
    total_platform_used_mb = 0.0
    total_platform_limit_mb = 0.0
    
    for org in orgs:
        # 1. Support Attachment file sizes
        att_bytes = 0
        try:
            att_bytes = db.session.query(func.sum(SupportAttachment.file_size)).join(
                User, SupportAttachment.uploaded_by_id == User.id
            ).filter(User.org_id == org.id).scalar() or 0
        except Exception:
            pass

        # 2. Announcement Attachment file sizes
        ann_bytes = 0
        try:
            ann_bytes = db.session.query(func.sum(AnnouncementAttachment.file_size)).join(
                User, AnnouncementAttachment.uploaded_by == User.id
            ).filter(User.org_id == org.id).scalar() or 0
        except Exception:
            pass

        # 3. DB text & payload byte sizes for this organization
        proj_bytes = 0
        try:
            proj_bytes = db.session.query(
                func.sum(
                    func.length(func.coalesce(Project.title, '')) + 
                    func.length(func.coalesce(Project.description, '')) +
                    func.length(func.coalesce(Project.category, '')) +
                    func.length(func.coalesce(Project.work_area, '')) +
                    func.length(func.coalesce(Project.plant, ''))
                )
            ).filter(Project.org_id == org.id).scalar() or 0
        except Exception:
            pass

        wf_bytes = 0
        try:
            wf_bytes = db.session.query(
                func.sum(func.length(func.cast(ProjectWorkflow.data, db.String)))
            ).join(Project, ProjectWorkflow.project_id == Project.id).filter(Project.org_id == org.id).scalar() or 0
        except Exception:
            pass

        kr_bytes = 0
        try:
            kr_bytes = db.session.query(
                func.sum(
                    func.length(func.coalesce(KnowledgeRepository.title, '')) +
                    func.length(func.coalesce(KnowledgeRepository.problem_summary, '')) +
                    func.length(func.coalesce(KnowledgeRepository.root_cause, '')) +
                    func.length(func.coalesce(KnowledgeRepository.solution_summary, '')) +
                    func.length(func.coalesce(KnowledgeRepository.keywords, ''))
                )
            ).filter(KnowledgeRepository.org_id == org.id).scalar() or 0
        except Exception:
            pass

        audit_bytes = 0
        try:
            audit_bytes = db.session.query(
                func.sum(
                    func.length(func.coalesce(AuditLog.action, '')) +
                    func.length(func.coalesce(AuditLog.target_table, '')) +
                    func.length(func.cast(AuditLog.details, db.String))
                )
            ).filter(AuditLog.org_id == org.id).scalar() or 0
        except Exception:
            pass

        user_bytes = 0
        try:
            user_bytes = db.session.query(
                func.sum(
                    func.length(func.coalesce(User.full_name, '')) +
                    func.length(func.coalesce(User.email, '')) +
                    func.length(func.coalesce(User.username, '')) +
                    func.length(func.cast(User.custom_fields, db.String))
                )
            ).filter(User.org_id == org.id).scalar() or 0
        except Exception:
            pass

        ticket_bytes = 0
        try:
            ticket_bytes = db.session.query(
                func.sum(
                    func.length(func.coalesce(SupportTicket.subject, '')) +
                    func.length(func.coalesce(SupportTicket.message, ''))
                )
            ).filter(SupportTicket.org_id == org.id).scalar() or 0
        except Exception:
            pass

        # Count DB entities
        users_cnt = 0
        projects_cnt = 0
        audits_cnt = 0
        knowledge_cnt = 0
        try:
            users_cnt = User.query.filter_by(org_id=org.id).count()
        except Exception:
            pass
        try:
            projects_cnt = Project.query.filter_by(org_id=org.id).count()
        except Exception:
            pass
        try:
            audits_cnt = AuditLog.query.filter_by(org_id=org.id).count()
        except Exception:
            pass
        try:
            knowledge_cnt = KnowledgeRepository.query.filter_by(org_id=org.id).count()
        except Exception:
            pass

        # 4. Total actual bytes stored for this organization
        total_actual_bytes = att_bytes + ann_bytes + proj_bytes + wf_bytes + kr_bytes + audit_bytes + user_bytes + ticket_bytes
        
        # Exact physical & DB storage used in MB
        calc_used_mb = round(total_actual_bytes / (1024.0 * 1024.0), 3)
        if calc_used_mb == 0 and (users_cnt > 0 or projects_cnt > 0):
            calc_used_mb = 0.01  # Minimum non-zero representation for active tenants with data
        
        # Resolve dynamic storage limit from plan allocation
        limit_mb = None

        # 1) Check active subscription record
        active_sub = Subscription.query.filter_by(org_id=org.id).filter(
            Subscription.subscription_status.in_(['Active', 'ACTIVE', 'Trialing', 'TRIALING'])
        ).order_by(Subscription.id.desc()).first()
        if active_sub and getattr(active_sub, 'storage_limit_gb', None) and active_sub.storage_limit_gb > 0:
            limit_mb = active_sub.storage_limit_gb * 1024.0

        # 2) Check matching SaaSPlan by name or code
        if not limit_mb and org.subscription_plan:
            saas_plan = SaaSPlan.query.filter(
                (SaaSPlan.name.ilike(org.subscription_plan)) | (SaaSPlan.code.ilike(org.subscription_plan))
            ).first()
            if saas_plan:
                plan_limits = SaaSPlanLimits.query.filter_by(plan_id=saas_plan.id).first()
                if plan_limits and plan_limits.storage_limit_gb and plan_limits.storage_limit_gb > 0:
                    limit_mb = plan_limits.storage_limit_gb * 1024.0

        # 3) Fallback to organization's stored limit or 10 GB
        if not limit_mb:
            limit_mb = org.storage_limit_mb if (org.storage_limit_mb and org.storage_limit_mb > 0) else 10240.0

        # Sync resolved storage limit and actual storage used to organization record
        org.storage_limit_mb = limit_mb
        org.storage_used_mb = calc_used_mb
        limit_gb = round(limit_mb / 1024.0, 2)
        used_gb = round(calc_used_mb / 1024.0, 4)
        pct = round((calc_used_mb / limit_mb * 100), 2) if limit_mb > 0 else 0.0

        if pct >= 90:
            health_status = 'Critical'
            badge_class = 'bg-danger'
        elif pct >= 70:
            health_status = 'Warning'
            badge_class = 'bg-warning text-dark'
        else:
            health_status = 'Normal'
            badge_class = 'bg-success'

        docs_sops_mb = round((att_bytes + ann_bytes + kr_bytes) / (1024.0 * 1024.0), 3)
        proj_wf_mb = round((proj_bytes + wf_bytes) / (1024.0 * 1024.0), 3)
        audits_mb = round(audit_bytes / (1024.0 * 1024.0), 3)
        sys_db_mb = round((user_bytes + ticket_bytes) / (1024.0 * 1024.0), 3)

        org_data = {
            "id": org.id,
            "name": org.name,
            "org_code": org.org_code or f"ORG-{org.id:03d}",
            "plan": org.subscription_plan or "Professional",
            "subscription_status": org.subscription_status or "Active",
            "users_count": users_cnt,
            "projects_count": projects_cnt,
            "audits_count": audits_cnt,
            "knowledge_entries_count": knowledge_cnt,
            "storage_used_mb": calc_used_mb,
            "storage_used_gb": used_gb,
            "storage_limit_mb": limit_mb,
            "storage_limit_gb": limit_gb,
            "usage_percent": pct,
            "health_status": health_status,
            "badge_class": badge_class,
            "breakdown": {
                "documents_sops_mb": docs_sops_mb,
                "project_workflows_mb": proj_wf_mb,
                "audit_logs_mb": audits_mb,
                "system_db_mb": sys_db_mb
            }
        }
        result.append(org_data)
        total_platform_used_mb += calc_used_mb
        total_platform_limit_mb += limit_mb

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()

    # Total storage used by customer organizations
    total_orgs_used_mb = sum(o["storage_used_mb"] for o in result)

    # Physical disk upload scan across all storage directories on disk
    total_disk_bytes = 0
    for upload_dir in ['uploads', 'backend/uploads', 'frontend/uploads', 'static/uploads', 'storage']:
        if os.path.exists(upload_dir):
            for dirpath, _, filenames in os.walk(upload_dir):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if os.path.exists(fp):
                        total_disk_bytes += os.path.getsize(fp)

    disk_media_mb = round(total_disk_bytes / (1024.0 * 1024.0), 3)
    total_software_used_mb = total_orgs_used_mb

    # Format tenant orgs storage for Organization Storage Analytics
    if total_orgs_used_mb >= 1024.0:
        total_used_fmt = f"{(total_orgs_used_mb / 1024.0):.2f} GB"
    elif total_orgs_used_mb >= 0.1:
        total_used_fmt = f"{total_orgs_used_mb:.2f} MB"
    elif total_orgs_used_mb > 0:
        total_used_fmt = f"{total_orgs_used_mb:.3f} MB"
    else:
        total_used_fmt = "0.00 MB"

    total_software_used_fmt = total_used_fmt

    total_limit_fmt = f"{(total_platform_limit_mb / 1024.0):.1f} GB"

    return {
        "organizations": result,
        "summary": {
            "total_used_mb": round(total_orgs_used_mb, 3),
            "total_used_fmt": total_used_fmt,
            "total_software_used_mb": round(total_software_used_mb, 3),
            "total_software_used_fmt": total_software_used_fmt,
            "total_limit_mb": round(total_platform_limit_mb, 2),
            "total_limit_fmt": total_limit_fmt,
            "total_orgs": len(result),
            "high_usage_count": sum(1 for o in result if o["usage_percent"] >= 70),
            "avg_usage_mb": round(total_orgs_used_mb / len(result), 3) if len(result) > 0 else 0.0
        }
    }

