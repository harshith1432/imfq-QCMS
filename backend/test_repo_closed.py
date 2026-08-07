from app import create_app, db
from app.infrastructure.database.models.models import Project, KnowledgeRepository

app = create_app()
with app.app_context():
    open_pids = [p.id for p in Project.query.filter(~Project.status.in_(['Closed', 'Completed', 'Archived'])).all()]
    if open_pids:
        del_count = KnowledgeRepository.query.filter(KnowledgeRepository.project_id.in_(open_pids)).delete(synchronize_session=False)
        db.session.commit()
        print(f"Cleaned up {del_count} open project entries from KnowledgeRepository table.", flush=True)

    repo_entries = KnowledgeRepository.query.all()
    print(f"\n=== KNOWLEDGE REPOSITORY ENTRIES COUNT: {len(repo_entries)} ===", flush=True)
    for r in repo_entries:
        p = Project.query.get(r.project_id)
        p_status = p.status if p else 'N/A'
        print(f"Entry ID: {r.id}, Project ID: {r.project_id}, Title: '{r.title}', Status: '{p_status}'", flush=True)
