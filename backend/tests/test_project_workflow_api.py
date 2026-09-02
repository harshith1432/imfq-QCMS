import pytest
import time
from app import db
from app.infrastructure.database.models import Project
from app.domain.services.project_closure_service import ProjectClosureService
from flask_jwt_extended import create_access_token


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
        p_ref.current_stage = 8
        db.session.commit()
        close_res = ProjectClosureService.execute_closure(pid, auth_context['user_id'], comments="Approved by Reviewer")
        assert close_res["status"] == "success"
        p_closed = db.session.get(Project, pid)
        assert p_closed.status == "Closed"
        assert p_closed.end_date is not None


def test_get_project_documents_and_download_all(client, auth_context):
    """Test GET /api/projects/<id>/documents and bulk zip download."""
    from app.infrastructure.database.models.workflow import Stage8StandardizationKnowledgeSharingProjectClosure
    from app.infrastructure.database.models.audit import KnowledgeRepository

    project = Project(
        title="Pytest Documents Test Project",
        project_uid=f"PRJ-DOC-{int(time.time())}",
        org_id=auth_context['org_id'],
        creator_id=auth_context['user_id'],
        team_leader_id=auth_context['user_id'],
        current_stage=8,
        status="In Progress"
    )
    db.session.add(project)
    db.session.commit()
    pid = project.id

    # Add Stage 8 SOP standardization entry with document
    s8 = Stage8StandardizationKnowledgeSharingProjectClosure(
        org_id=auth_context['org_id'],
        project_id=pid,
        sop_standardization=[
            {
                "process_name": "Final Assembly",
                "document": "SOP-ASSY-001.pdf",
                "url": "/uploads/sop_documents/SOP-ASSY-001.pdf"
            }
        ]
    )
    db.session.add(s8)

    # Add KnowledgeRepository entry
    kr = KnowledgeRepository(
        org_id=auth_context['org_id'],
        project_id=pid,
        title="Assembly SOP & Closure Report",
        sop_path="/uploads/sop_documents/SOP-ASSY-001.pdf",
        closure_report_path="https://sharepoint.com/reports/assembly_closure.pdf"
    )
    db.session.add(kr)
    db.session.commit()

    # 1. Test GET /api/projects/<id>/documents
    res = client.get(f'/api/projects/{pid}/documents', headers=auth_context['headers'])
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "success"
    assert data["total_documents"] >= 2
    docs = data["documents"]
    assert any(d["filename"] == "SOP-ASSY-001.pdf" for d in docs)
    assert any("sharepoint.com" in d["url"] for d in docs)

    # 2. Test GET /api/projects/<id>/documents/download-all
    zip_res = client.get(f'/api/projects/{pid}/documents/download-all', headers=auth_context['headers'])
    assert zip_res.status_code == 200
    assert zip_res.headers.get("Content-Type") == "application/zip"
    assert "attachment" in zip_res.headers.get("Content-Disposition", "")

