"""
Debug script: run from the backend directory.
Usage: python scratch/debug_reviewer_queue.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.infrastructure.database.models.models import (
    Project, ProjectStageTracker, ProjectWorkflow, User
)
from app import db

app = create_app()

with app.app_context():
    print("\n=== ALL PROJECTS ===")
    projects = Project.query.all()
    for p in projects:
        print(f"  id={p.id} uid={p.project_uid} title={p.title!r} "
              f"current_stage={p.current_stage} status={p.status!r} "
              f"reviewer_id={p.reviewer_id} org_id={p.org_id}")

    print("\n=== ALL STAGE TRACKERS (status=Submitted For Review) ===")
    trackers = ProjectStageTracker.query.filter_by(status='Submitted For Review').all()
    for t in trackers:
        print(f"  project_id={t.project_id} stage_number={t.stage_number} status={t.status!r}")

    print("\n=== ALL REVIEWERS ===")
    reviewers = User.query.join(User.role).filter_by(name='Reviewer').all()
    for r in reviewers:
        print(f"  id={r.id} username={r.username!r} dept={getattr(r.dept, 'name', None)} org_id={r.org_id}")

    print("\n=== MATCHING LOGIC CHECK ===")
    for reviewer in reviewers:
        from sqlalchemy import or_
        query = Project.query.filter(
            Project.org_id == reviewer.org_id,
            or_(
                Project.reviewer_id == reviewer.id,
                Project.reviewer_id == None
            )
        )
        matched = query.all()
        print(f"\nReviewer {reviewer.username!r} (id={reviewer.id}):")
        for p in matched:
            tracker = ProjectStageTracker.query.filter_by(
                project_id=p.id, stage_number=p.current_stage
            ).first()
            tracker_status = tracker.status if tracker else 'NO TRACKER'
            print(f"  Project {p.project_uid} stage={p.current_stage} "
                  f"status={p.status!r} tracker_status={tracker_status!r}")
            if tracker and tracker.status == 'Submitted For Review':
                print(f"    ✅ WOULD APPEAR IN PENDING QUEUE")
            else:
                print(f"    ❌ NOT in pending queue (tracker_status={tracker_status!r})")
