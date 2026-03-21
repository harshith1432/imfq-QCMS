
import traceback
from app import create_app, db
from app.models import User, Project, ProjectWorkflow, Stage3RCA, Stage8Standardization, Stage7Impact, KnowledgeRepository, AuditLog
from datetime import datetime

app = create_app()
with app.app_context():
    project_id = 6
    org_id = 2
    user_id = 2 # Harshith2
    
    try:
        project = Project.query.filter_by(id=project_id, org_id=org_id).first()
        if not project:
            print('Project not found')
            exit(1)
            
        print(f'Attempting closure for project: {project.title}')
        
        # Mimic close_project logic
        project.status = 'Closed'
        project.end_date = datetime.utcnow().date()
        
        # Archive
        existing = KnowledgeRepository.query.filter_by(project_id=project_id, org_id=org_id).first()
        if not existing:
            stage1 = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=1, org_id=org_id).first()
            rca = Stage3RCA.query.filter_by(project_id=project_id, org_id=org_id).first()
            stage4 = ProjectWorkflow.query.filter_by(project_id=project_id, stage_id=4, org_id=org_id).first()
            impact = Stage7Impact.query.filter_by(project_id=project_id, org_id=org_id).first()
            std = Stage8Standardization.query.filter_by(project_id=project_id, org_id=org_id).first()
            
            entry = KnowledgeRepository(
                project_id=project_id,
                org_id=org_id,
                title=project.title,
                department_id=project.department_id,
                category=project.category,
                problem_summary=stage1.data.get('problem_statement', '') if stage1 and stage1.data else '',
                root_cause=rca.root_cause_summary if rca else '',
                solution_summary=stage4.data.get('proposed_solution', '') if stage4 and stage4.data else '',
                kpi_improvement_pct=impact.kpi_improvement_pct if impact else 0,
                cost_savings=impact.cost_savings if impact else 0,
                sop_path=std.sop_url if std else None,
                closure_report_path=std.closure_report_path if std else None,
                tags=[project.category] if project.category else [],
                keywords=f"{project.title} {project.category or ''}",
                archived_at=datetime.utcnow()
            )
            db.session.add(entry)
            print('KnowledgeRepository entry added')
        else:
            print('KnowledgeRepository entry already exists')
        
        # Log (using AuditLog directly instead of log_action to avoid commit in the middle)
        log = AuditLog(
            user_id=user_id,
            org_id=org_id,
            action='PROJECT_CLOSED',
            target_table='projects',
            target_id=project_id,
            details={'title': project.title}
        )
        db.session.add(log)
        print('AuditLog entry added')
        
        db.session.commit()
        print('Commit SUCCESSFUL')
        
    except Exception as e:
        print('EXCEPTION CAUGHT:')
        traceback.print_exc()
        db.session.rollback()
