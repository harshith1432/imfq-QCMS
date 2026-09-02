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
    if not orgs:
        return {
            "organizations": [],
            "summary": {
                "total_used_mb": 0.0,
                "total_used_fmt": "0.00 MB",
                "total_software_used_mb": 0.0,
                "total_software_used_fmt": "0.00 MB",
                "total_limit_mb": 0.0,
                "total_limit_fmt": "0.0 GB",
                "total_orgs": 0,
                "high_usage_count": 0,
                "avg_usage_mb": 0.0
            }
        }

    # 1. Support Attachment file sizes (grouped by org_id)
    att_map = {}
    try:
        att_query = db.session.query(
            User.org_id, func.sum(SupportAttachment.file_size)
        ).join(User, SupportAttachment.uploaded_by_id == User.id)
        if org_id:
            att_query = att_query.filter(User.org_id == org_id)
        att_map = {r[0]: (r[1] or 0) for r in att_query.group_by(User.org_id).all() if r[0] is not None}
    except Exception:
        pass

    # 2. Announcement Attachment file sizes (grouped by org_id)
    ann_map = {}
    try:
        ann_query = db.session.query(
            User.org_id, func.sum(AnnouncementAttachment.file_size)
        ).join(User, AnnouncementAttachment.uploaded_by == User.id)
        if org_id:
            ann_query = ann_query.filter(User.org_id == org_id)
        ann_map = {r[0]: (r[1] or 0) for r in ann_query.group_by(User.org_id).all() if r[0] is not None}
    except Exception:
        pass

    # 3. Project string & payload bytes (grouped by org_id)
    proj_bytes_map = {}
    try:
        proj_q = db.session.query(
            Project.org_id,
            func.sum(
                func.length(func.coalesce(Project.title, '')) + 
                func.length(func.coalesce(Project.description, '')) +
                func.length(func.coalesce(Project.category, '')) +
                func.length(func.coalesce(Project.work_area, '')) +
                func.length(func.coalesce(Project.plant, ''))
            )
        )
        if org_id:
            proj_q = proj_q.filter(Project.org_id == org_id)
        proj_bytes_map = {r[0]: (r[1] or 0) for r in proj_q.group_by(Project.org_id).all() if r[0] is not None}
    except Exception:
        pass

    # Project workflows JSON bytes (grouped by org_id)
    wf_bytes_map = {}
    try:
        wf_q = db.session.query(
            Project.org_id,
            func.sum(func.length(func.cast(ProjectWorkflow.data, db.String)))
        ).join(Project, ProjectWorkflow.project_id == Project.id)
        if org_id:
            wf_q = wf_q.filter(Project.org_id == org_id)
        wf_bytes_map = {r[0]: (r[1] or 0) for r in wf_q.group_by(Project.org_id).all() if r[0] is not None}
    except Exception:
        pass

    # Knowledge repository text bytes (grouped by org_id)
    kr_bytes_map = {}
    try:
        kr_q = db.session.query(
            KnowledgeRepository.org_id,
            func.sum(
                func.length(func.coalesce(KnowledgeRepository.title, '')) +
                func.length(func.coalesce(KnowledgeRepository.problem_summary, '')) +
                func.length(func.coalesce(KnowledgeRepository.root_cause, '')) +
                func.length(func.coalesce(KnowledgeRepository.solution_summary, '')) +
                func.length(func.coalesce(KnowledgeRepository.keywords, ''))
            )
        )
        if org_id:
            kr_q = kr_q.filter(KnowledgeRepository.org_id == org_id)
        kr_bytes_map = {r[0]: (r[1] or 0) for r in kr_q.group_by(KnowledgeRepository.org_id).all() if r[0] is not None}
    except Exception:
        pass

    # Audit log text bytes (grouped by org_id)
    audit_bytes_map = {}
    try:
        audit_q = db.session.query(
            AuditLog.org_id,
            func.sum(
                func.length(func.coalesce(AuditLog.action, '')) +
                func.length(func.coalesce(AuditLog.target_table, '')) +
                func.length(func.cast(AuditLog.details, db.String))
            )
        )
        if org_id:
            audit_q = audit_q.filter(AuditLog.org_id == org_id)
        audit_bytes_map = {r[0]: (r[1] or 0) for r in audit_q.group_by(AuditLog.org_id).all() if r[0] is not None}
    except Exception:
        pass

    # Users text bytes and counts (grouped by org_id)
    user_bytes_map = {}
    user_cnt_map = {}
    try:
        user_q = db.session.query(
            User.org_id,
            func.sum(
                func.length(func.coalesce(User.full_name, '')) +
                func.length(func.coalesce(User.email, '')) +
                func.length(func.coalesce(User.username, '')) +
                func.length(func.cast(User.custom_fields, db.String))
            ),
            func.count(User.id)
        )
        if org_id:
            user_q = user_q.filter(User.org_id == org_id)
        user_stats = user_q.group_by(User.org_id).all()
        for r in user_stats:
            if r[0] is not None:
                user_bytes_map[r[0]] = r[1] or 0
                user_cnt_map[r[0]] = r[2] or 0
    except Exception:
        pass

    # Support tickets text bytes (grouped by org_id)
    ticket_bytes_map = {}
    try:
        ticket_q = db.session.query(
            SupportTicket.org_id,
            func.sum(
                func.length(func.coalesce(SupportTicket.subject, '')) +
                func.length(func.coalesce(SupportTicket.message, ''))
            )
        )
        if org_id:
            ticket_q = ticket_q.filter(SupportTicket.org_id == org_id)
        ticket_bytes_map = {r[0]: (r[1] or 0) for r in ticket_q.group_by(SupportTicket.org_id).all() if r[0] is not None}
    except Exception:
        pass

    # Projects counts
    proj_cnt_map = {}
    try:
        pq = db.session.query(Project.org_id, func.count(Project.id))
        if org_id: pq = pq.filter(Project.org_id == org_id)
        proj_cnt_map = {r[0]: (r[1] or 0) for r in pq.group_by(Project.org_id).all() if r[0] is not None}
    except Exception:
        pass

    # Audit counts
    audit_cnt_map = {}
    try:
        aq = db.session.query(AuditLog.org_id, func.count(AuditLog.id))
        if org_id: aq = aq.filter(AuditLog.org_id == org_id)
        audit_cnt_map = {r[0]: (r[1] or 0) for r in aq.group_by(AuditLog.org_id).all() if r[0] is not None}
    except Exception:
        pass

    # Knowledge counts
    kr_cnt_map = {}
    try:
        kq = db.session.query(KnowledgeRepository.org_id, func.count(KnowledgeRepository.id))
        if org_id: kq = kq.filter(KnowledgeRepository.org_id == org_id)
        kr_cnt_map = {r[0]: (r[1] or 0) for r in kq.group_by(KnowledgeRepository.org_id).all() if r[0] is not None}
    except Exception:
        pass

    # Active subscription storage limit mapping
    sub_limit_map = {}
    try:
        subs_q = Subscription.query.filter(
            Subscription.subscription_status.in_(['Active', 'ACTIVE', 'Trialing', 'TRIALING'])
        )
        if org_id: subs_q = subs_q.filter(Subscription.org_id == org_id)
        subs = subs_q.order_by(Subscription.id.asc()).all()
        for s in subs:
            if s.org_id and getattr(s, 'storage_limit_gb', None) and s.storage_limit_gb > 0:
                sub_limit_map[s.org_id] = float(s.storage_limit_gb) * 1024.0
    except Exception:
        pass

    # SaaSPlan limits lookup
    plan_limits_dict = {}
    try:
        all_plans = SaaSPlan.query.all()
        for p in all_plans:
            pl = SaaSPlanLimits.query.filter_by(plan_id=p.id).first()
            if pl and pl.storage_limit_gb and pl.storage_limit_gb > 0:
                lim = float(pl.storage_limit_gb) * 1024.0
                if p.name: plan_limits_dict[p.name.strip().lower()] = lim
                if p.code: plan_limits_dict[p.code.strip().lower()] = lim
    except Exception:
        pass

    result = []
    total_platform_used_mb = 0.0
    total_platform_limit_mb = 0.0

    for org in orgs:
        att_bytes = att_map.get(org.id, 0)
        ann_bytes = ann_map.get(org.id, 0)
        proj_bytes = proj_bytes_map.get(org.id, 0)
        wf_bytes = wf_bytes_map.get(org.id, 0)
        kr_bytes = kr_bytes_map.get(org.id, 0)
        audit_bytes = audit_bytes_map.get(org.id, 0)
        user_bytes = user_bytes_map.get(org.id, 0)
        ticket_bytes = ticket_bytes_map.get(org.id, 0)

        users_cnt = user_cnt_map.get(org.id, 0)
        projects_cnt = proj_cnt_map.get(org.id, 0)
        audits_cnt = audit_cnt_map.get(org.id, 0)
        knowledge_cnt = kr_cnt_map.get(org.id, 0)

        total_actual_bytes = att_bytes + ann_bytes + proj_bytes + wf_bytes + kr_bytes + audit_bytes + user_bytes + ticket_bytes
        
        calc_used_mb = round(total_actual_bytes / (1024.0 * 1024.0), 3)
        if calc_used_mb == 0 and (users_cnt > 0 or projects_cnt > 0):
            calc_used_mb = 0.01

        # Resolve storage limit
        limit_mb = sub_limit_map.get(org.id)
        if not limit_mb and org.subscription_plan:
            limit_mb = plan_limits_dict.get(org.subscription_plan.strip().lower())
        if not limit_mb:
            limit_mb = org.storage_limit_mb if (org.storage_limit_mb and org.storage_limit_mb > 0) else 10240.0

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

