import sys
from datetime import datetime

with open("delivery_out.txt", "w", encoding="utf-8") as f:
    sys.stdout = f
    sys.stderr = f
    try:
        from app import create_app, db
        from app.infrastructure.database.models.models import Project, ProjectStageTracker, Stage8Implementation, KnowledgeRepository, Organization

        app = create_app()
        with app.app_context():
            print("=== INSPECTING COMPLETED PROJECTS & DELIVERY TIMES ===")
            orgs = Organization.query.all()
            for org in orgs:
                completed_projects = Project.query.filter(
                    Project.org_id == org.id,
                    Project.status.in_(['Closed', 'Completed', 'Archived'])
                ).all()
                
                if not completed_projects:
                    continue

                print(f"\nOrg ID: {org.id}, Name: '{org.name}', Completed Projects Count: {len(completed_projects)}")
                
                delivery_days_list = []
                for p in completed_projects:
                    # Determine start datetime
                    p_start = p.created_at
                    if not p_start and p.start_date:
                        p_start = datetime.combine(p.start_date, datetime.min.time())
                    
                    st1 = ProjectStageTracker.query.filter_by(project_id=p.id, stage_number=1).first()
                    if st1 and st1.started_at:
                        if not p_start or st1.started_at < p_start:
                            p_start = st1.started_at
                            
                    # Determine end datetime (completion / delivery time)
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
                            
                    days = 0.0
                    if p_start and p_end:
                        delta = (p_end - p_start).total_seconds() / 86400.0
                        days = max(round(delta, 1), 0.5)
                        delivery_days_list.append(days)
                    elif p_start:
                        delta = (datetime.utcnow() - p_start).total_seconds() / 86400.0
                        days = max(round(delta, 1), 1.0)
                        delivery_days_list.append(days)
                        
                    print(f"  - Project ID: {p.id}, Title: '{p.title}', Status: '{p.status}', Start: {p_start}, End: {p_end} => Delivery: {days} Days")
                    
                avg_delivery = round(sum(delivery_days_list) / len(delivery_days_list), 1) if delivery_days_list else 0.0
                print(f"  => Real-time Avg Delivery Time for Org {org.id}: {avg_delivery} Days (List: {delivery_days_list})")
    except Exception as e:
        import traceback
        traceback.print_exc()
