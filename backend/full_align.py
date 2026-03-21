
from app import create_app, db
from app.models import (
    Project, User, ProjectStageTracker, ProjectWorkflow, 
    Stage1Problem, Stage2Data, Stage3RCA, Stage4Solution, 
    Stage5Approval, Stage6Implementation, Stage7Impact, 
    Stage8Standardization, AuditLog, KnowledgeRepository,
    KPIMetric, FacilitatorNote
)
import sqlalchemy as sa

app = create_app()
with app.app_context():
    target_org_id = 1
    
    projects = Project.query.filter_by(org_id=target_org_id).all()
    project_ids = [p.id for p in projects]
    print(f"Aligning data for projects: {project_ids}")

    models = [
        ProjectStageTracker, ProjectWorkflow, Stage1Problem, 
        Stage2Data, Stage3RCA, Stage4Solution, 
        Stage5Approval, Stage6Implementation, Stage7Impact, 
        Stage8Standardization, KPIMetric, FacilitatorNote,
        KnowledgeRepository
    ]

    for model in models:
        try:
            count = model.query.filter(model.project_id.in_(project_ids)).update(
                {model.org_id: target_org_id}, synchronize_session=False
            )
            print(f"Updated {count} records in {model.__tablename__}")
        except Exception as e:
            print(f"Error updating {model.__tablename__}: {e}")

    # Align AuditLogs for these projects
    log_count = AuditLog.query.filter(
        AuditLog.target_table == 'projects', 
        AuditLog.target_id.in_([str(pid) for pid in project_ids])
    ).update({AuditLog.org_id: target_org_id}, synchronize_session=False)
    print(f"Updated {log_count} audit logs")

    db.session.commit()
    print("Alignment complete.")
