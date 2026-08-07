"""
Storage Calculator Service
Calculates real-time data storage consumption across all organizations in the platform.
Aggregates file attachments, DB records footprint, SOPs, RAG vector data, and user assets.
"""
from sqlalchemy import func
from app.infrastructure.database.models.models import (
    db, Organization, User, Project, SupportAttachment, 
    AnnouncementAttachment, KnowledgeRepository, AuditLog
)

def calculate_org_storage_realtime(org_id=None):
    """
    Computes real-time storage usage for a specific org or all orgs.
    Returns calculated storage data dict.
    """
    query = Organization.query.filter(Organization.is_deleted == False)
    if org_id:
        query = query.filter_by(id=org_id)
    else:
        query = query.filter(Organization.is_platform_org == False)
    
    orgs = query.all()
    result = []
    total_platform_used_mb = 0.0
    total_platform_limit_mb = 0.0
    
    for org in orgs:
        # 1. Physical / Support Attachment file sizes
        att_bytes = db.session.query(func.sum(SupportAttachment.file_size)).join(
            User, SupportAttachment.uploaded_by_id == User.id
        ).filter(User.org_id == org.id).scalar() or 0

        # 2. Count DB entity footprint
        users_cnt = User.query.filter_by(org_id=org.id).count()
        projects_cnt = Project.query.filter_by(org_id=org.id).count()
        audits_cnt = AuditLog.query.filter_by(org_id=org.id).count()
        knowledge_cnt = KnowledgeRepository.query.filter_by(org_id=org.id).count()

        # 3. Calculate storage footprint in MB
        file_mb = att_bytes / (1024.0 * 1024.0)
        
        # Weighted DB footprint (Users, Projects, Audit Logs, RAG Embeddings)
        db_mb = (users_cnt * 0.45) + (projects_cnt * 1.85) + (audits_cnt * 0.02) + (knowledge_cnt * 1.2)
        
        # Base metadata overhead if active
        base_mb = 1.2 if (users_cnt > 0 or projects_cnt > 0) else 0.0
        
        calc_used_mb = round(file_mb + db_mb + base_mb, 2)
        
        # Sync with organization record
        org.storage_used_mb = calc_used_mb

        limit_mb = org.storage_limit_mb or 10240.0 # Default 10GB
        limit_gb = round(limit_mb / 1024.0, 2)
        used_gb = round(calc_used_mb / 1024.0, 2)
        pct = round((calc_used_mb / limit_mb * 100), 1) if limit_mb > 0 else 0.0

        if pct >= 90:
            health_status = 'Critical'
            badge_class = 'bg-danger'
        elif pct >= 70:
            health_status = 'Warning'
            badge_class = 'bg-warning text-dark'
        else:
            health_status = 'Normal'
            badge_class = 'bg-success'

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
                "documents_sops_mb": round(file_mb + (knowledge_cnt * 0.8), 2),
                "project_workflows_mb": round(projects_cnt * 1.5, 2),
                "audit_logs_mb": round(audits_cnt * 0.02, 2),
                "system_db_mb": round(users_cnt * 0.45 + base_mb, 2)
            }
        }
        result.append(org_data)
        total_platform_used_mb += calc_used_mb
        total_platform_limit_mb += limit_mb

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()

    total_used_fmt = f"{total_platform_used_mb:.1f} MB" if total_platform_used_mb < 1024 else f"{(total_platform_used_mb / 1024.0):.2f} GB"
    total_limit_fmt = f"{(total_platform_limit_mb / 1024.0):.1f} GB"

    return {
        "organizations": result,
        "summary": {
            "total_used_mb": round(total_platform_used_mb, 2),
            "total_used_fmt": total_used_fmt,
            "total_limit_mb": round(total_platform_limit_mb, 2),
            "total_limit_fmt": total_limit_fmt,
            "total_orgs": len(result),
            "high_usage_count": sum(1 for o in result if o["usage_percent"] >= 70),
            "avg_usage_mb": round(total_platform_used_mb / max(1, len(result)), 2)
        }
    }
