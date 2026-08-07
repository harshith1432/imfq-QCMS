import sys
with open("v_out.txt", "w") as out_f:
    try:
        from app import create_app, db
        from app.infrastructure.database.models.models import Project, ProjectStageTracker, Stage8Implementation, KnowledgeRepository
        from datetime import datetime

        app = create_app()
        with app.app_context():
            org_id = 3
            completed_projects_list = Project.query.filter(
                Project.org_id == org_id,
                Project.status.in_(['Closed', 'Completed', 'Archived'])
            ).all()

            delivery_days_list = []
            for p in completed_projects_list:
                p_start = p.created_at
                if not p_start and p.start_date:
                    p_start = datetime.combine(p.start_date, datetime.min.time())
                
                st1 = ProjectStageTracker.query.filter_by(project_id=p.id, stage_number=1).first()
                if st1 and st1.started_at:
                    if not p_start or st1.started_at < p_start:
                        p_start = st1.started_at
                        
                p_end = None
                st8 = ProjectStageTracker.query.filter_by(project_id=p.id, stage_number=8).first()
                if st8 and st8.completed_at:
                    p_end = st8.completed_at
                
                if not p_end:
                    s8_impl = Stage8Implementation.query.filter_by(project_id=p.id).first()
                    if s8_impl and getattr(s8_impl, 'created_at', None):
                        p_end = s8_impl.created_at
                        
                if not p_end:
                    repo = KnowledgeRepository.query.filter_by(project_id=p.id).first()
                    if repo and repo.archived_at:
                        p_end = repo.archived_at
                        
                if not p_end and p.end_date:
                    p_end = datetime.combine(p.end_date, datetime.min.time())
                    
                if not p_end:
                    max_comp = db.session.query(db.func.max(ProjectStageTracker.completed_at)).filter_by(project_id=p.id).scalar()
                    if max_comp:
                        p_end = max_comp
                        
                if p_start and p_end:
                    delta_days = (p_end - p_start).total_seconds() / 86400.0
                    delivery_days_list.append(max(round(delta_days, 1), 0.1))
                elif p_start:
                    delta_days = (datetime.utcnow() - p_start).total_seconds() / 86400.0
                    delivery_days_list.append(max(round(delta_days, 1), 0.1))

            avg_velocity = round(sum(delivery_days_list) / len(delivery_days_list), 1) if delivery_days_list else 0.0

            out_f.write("=========================================\n")
            out_f.write(f"Org ID: {org_id} ('youtube')\n")
            out_f.write(f"Total Completed Projects: {len(completed_projects_list)}\n")
            out_f.write(f"Individual Project Durations: {delivery_days_list}\n")
            out_f.write(f"REAL-TIME AVG DELIVERY TIME: {avg_velocity} Days\n")
            out_f.write("=========================================\n")
    except Exception as e:
        out_f.write(str(e))
