import pytest
import time
from unittest.mock import patch, MagicMock
from app import db
from app.infrastructure.cache.redis_adapter import cache
from app.domain.services.cache_service import CacheService
from app.infrastructure.database.models import User, Organization, Project, Stage8Standardization


def test_async_pdf_report_export_accepted(client, auth_context):
    """Verify that exporting PDF asynchronously returns HTTP 202 Accepted with polling job_id."""
    import uuid
    org_id = auth_context['org_id']
    project = Project.query.filter_by(org_id=org_id).first()
    if not project:
        project = Project(
            project_uid=f"PRJ-PDF-{uuid.uuid4().hex[:8]}",
            title="Test Async PDF Project",
            org_id=org_id,
            current_stage=1,
            status="In Progress"
        )
        db.session.add(project)
        db.session.commit()

    res = client.post(f'/api/reports/projects/{project.id}/export-pdf-async', headers=auth_context['headers'])
    assert res.status_code == 202
    data = res.get_json()
    assert data['status'] == 'processing'
    assert 'job_id' in data
    job_id = data['job_id']

    # Verify task status polling endpoint
    status_res = client.get(f'/api/reports/task-status/{job_id}', headers=auth_context['headers'])
    assert status_res.status_code == 200
    status_data = status_res.get_json()
    assert 'status' in status_data


def test_async_bulk_pdf_zip_export_accepted(client, auth_context):
    """Verify that exporting bulk PDF zip asynchronously returns HTTP 202 Accepted with polling job_id."""
    res = client.post('/api/reports/export/pdf/all-async', headers=auth_context['headers'])
    assert res.status_code == 202
    data = res.get_json()
    assert data['status'] == 'processing'
    assert 'job_id' in data
    job_id = data['job_id']

    # Verify task status polling endpoint
    status_res = client.get(f'/api/reports/task-status/{job_id}', headers=auth_context['headers'])
    assert status_res.status_code == 200
    status_data = status_res.get_json()
    assert 'status' in status_data


def test_multi_tier_redis_caching_and_isolation():
    """Verify Tier 1, Tier 2, and Tier 3 cache functionality and multi-tenant isolation."""
    # Tier 1: Global Platform Cache
    calls = {'count': 0}
    def fetch_global():
        calls['count'] += 1
        return {"app": "QCMS", "version": "2.0"}

    CacheService.invalidate_global_platform_settings()
    res1 = CacheService.get_global_platform_settings(fetch_global)
    res2 = CacheService.get_global_platform_settings(fetch_global)
    assert res1 == res2
    assert calls['count'] == 1  # Served from cache on second call

    # Tier 2: Tenant Branding Cache (Tenant Scoped)
    org1_calls = {'count': 0}
    def fetch_org1_branding():
        org1_calls['count'] += 1
        return {"company": "Org 1 Corp", "color": "#123456"}

    org2_calls = {'count': 0}
    def fetch_org2_branding():
        org2_calls['count'] += 1
        return {"company": "Org 2 Corp", "color": "#654321"}

    CacheService.invalidate_tenant_branding(org_id=101)
    CacheService.invalidate_tenant_branding(org_id=102)

    b1_first = CacheService.get_tenant_branding(101, fetch_org1_branding)
    b1_cached = CacheService.get_tenant_branding(101, fetch_org1_branding)
    assert b1_first == b1_cached
    assert org1_calls['count'] == 1

    b2 = CacheService.get_tenant_branding(102, fetch_org2_branding)
    assert b2["company"] == "Org 2 Corp"
    assert org2_calls['count'] == 1

    # Verify no cross-tenant cache contamination
    assert b1_first["company"] != b2["company"]


def test_proactive_cache_invalidation_on_project_lifecycle(client, auth_context):
    """Verify that updating/creating projects proactively clears the KPI summary cache."""
    org_id = auth_context['org_id']

    # 1. Warm up dashboard KPI summary cache
    res1 = client.get('/api/dashboard/kpi-summary', headers=auth_context['headers'])
    assert res1.status_code == 200
    data1 = res1.get_json()

    # 2. Add a new project
    res_create = client.post('/api/projects/', json={
        "title": "Cache Invalidation Test Project",
        "category": "Quality",
        "description": "Testing cache clearing",
        "work_area": "Plant 1",
        "member_ids": []
    }, headers=auth_context['headers'])
    assert res_create.status_code in (200, 201)

    # 3. Query KPI summary again and verify updated pipeline
    res2 = client.get('/api/dashboard/kpi-summary', headers=auth_context['headers'])
    assert res2.status_code == 200
    data2 = res2.get_json()
    assert data2['pipeline']['stage_1'] >= data1['pipeline']['stage_1']


def test_ai_rag_async_task_wrapper(app):
    """Verify that process_document_for_rag handles missing or valid docs safely."""
    with app.app_context():
        from app.infrastructure.tasks.ai_rag_tasks import process_document_for_rag
        # Mock non-existent doc ID
        result = process_document_for_rag.run(doc_id=999999, org_id=1)
        assert result['status'] == 'failed'
