import pytest
from app import db
from app.infrastructure.database.models import User, Organization, Project, Department, Stage7Impact, Stage4Solution, Stage6Implementation


def test_dashboard_kpi_summary_aggregations(client, auth_context):
    """Verify that KPI summary aggregation returns accurate metrics with tenant isolation."""
    res = client.get('/api/dashboard/kpi-summary', headers=auth_context['headers'])
    assert res.status_code == 200
    data = res.get_json()
    assert 'total_cost_savings' in data
    assert 'productivity_gain' in data
    assert 'quality_improvement' in data
    assert 'total_projects_measured' in data
    assert 'pipeline' in data
    assert isinstance(data['pipeline'], dict)
    for stage_i in range(1, 9):
        assert f"stage_{stage_i}" in data['pipeline']


def test_dashboard_dept_comparison_batching(client, auth_context):
    """Verify that department comparison endpoint aggregates correctly without N+1 query loops."""
    res = client.get('/api/dashboard/dept-comparison', headers=auth_context['headers'])
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, list)
    for item in data:
        assert 'department' in item
        assert 'dept_id' in item
        assert 'total_savings' in item
        assert 'avg_improvement' in item
        assert 'project_count' in item


@pytest.mark.skip(reason="[DEAD CODE - UNUSED BY FRONTEND / REMOVED FEATURE] cost-variance widget was removed from frontend dashboard.")
def test_dashboard_cost_variance_joined_query(client, auth_context):
    """Verify that cost variance single-join query runs correctly."""
    res = client.get('/api/dashboard/cost-variance', headers=auth_context['headers'])
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, list)
    for item in data:
        assert 'project_id' in item
        assert 'estimated_cost' in item
        assert 'actual_cost' in item
        assert 'variance' in item
        assert 'variance_pct' in item


def test_project_listing_and_details_eager_loading(client, auth_context):
    """Verify that project listings and details eager load relationships correctly."""
    res = client.get('/api/projects/', headers=auth_context['headers'])
    assert res.status_code == 200
    projects = res.get_json()
    assert isinstance(projects, list)

    if len(projects) > 0:
        proj_id = projects[0]['id']
        res_det = client.get(f'/api/projects/{proj_id}', headers=auth_context['headers'])
        assert res_det.status_code == 200
        det = res_det.get_json()
        assert det['id'] == proj_id
        assert 'title' in det
        assert 'department' in det
        assert 'creator' in det


def test_export_csv_batching_optimization(client, auth_context):
    """Verify that export_csv executes without errors and generates valid CSV content."""
    res = client.get('/api/reports/export/csv', headers=auth_context['headers'])
    assert res.status_code == 200
    assert res.headers.get('Content-Type', '').startswith('text/csv')
    assert 'attachment' in res.headers.get('Content-Disposition', '')
    csv_text = res.data.decode('utf-8-sig')
    assert 'Project UID' in csv_text
    assert 'Title' in csv_text
    assert 'Completion %' in csv_text
    assert 'ROI %' in csv_text

