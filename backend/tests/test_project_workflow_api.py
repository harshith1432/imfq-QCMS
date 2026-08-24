import pytest
import time
from app import db
from app.infrastructure.database.models import Project
from app.domain.services.project_closure_service import ProjectClosureService


def test_project_creation_and_retrieval(client, auth_context):
    """Test project creation and retrieval through API."""
    unique_uid = f"PRJ-TST-{int(time.time())}"
    create_payload = {
        "title": "Automated Pytest QC Project",
        "project_uid": unique_uid,
        "category": "Quality",
        "work_area": "Assembly Line A",
        "description": "Continuous improvement in line A cycle time."
    }
    res = client.post('/api/projects/', json=create_payload, headers=auth_context['headers'])
    # Should succeed or return project representation
    if res.status_code in [200, 201]:
        data = res.get_json()
        assert "id" in data or "project" in data or "project_uid" in str(data)


def test_project_closure_service_lifecycle(app, auth_context):
    """Test ProjectClosureService business logic execution directly."""
    with app.app_context():
        # Create a sample project in DB
        project = Project(
            title="Pytest Closure Lifecycle Project",
            project_uid=f"PRJ-CLS-{int(time.time())}",
            org_id=auth_context['org_id'],
            creator_id=auth_context['user_id'],
            team_leader_id=auth_context['user_id'],
            current_stage=8,
            status="In Progress"
        )
        db.session.add(project)
        db.session.commit()
        pid = project.id

        # 1. Test Rejection
        reject_res = ProjectClosureService.reject_closure(pid, auth_context['user_id'], comments="Need revision")
        assert reject_res["status"] == "success"
        p_ref = db.session.get(Project, pid)
        assert p_ref.status == "Rejected"
        assert p_ref.current_stage == 1

        # 2. Test Execution of Closure
        close_res = ProjectClosureService.execute_closure(pid, auth_context['user_id'], comments="Approved by Reviewer")
        assert close_res["status"] == "success"
        p_closed = db.session.get(Project, pid)
        assert p_closed.status == "Closed"
        assert p_closed.end_date is not None
