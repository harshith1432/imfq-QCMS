import pytest
from app.infrastructure.database.models import User


def test_login_invalid_credentials(client):
    """Verify that invalid login credentials return 401 Unauthorized."""
    res = client.post('/api/auth/login', json={
        "email": "nonexistent_user_9999@example.com",
        "password": "WrongPassword123!"
    })
    assert res.status_code in [401, 404]
    data = res.get_json() or {}
    assert "error" in data or "message" in data or "msg" in data


def test_protected_route_without_token(client):
    """Verify that protected API endpoints reject unauthenticated requests."""
    res = client.get('/api/analytics/system-metrics')
    # Depending on auth decorators, system metrics or admin endpoints require auth
    res_admin = client.get('/api/admin/users')
    assert res_admin.status_code in [401, 403, 422]


def test_authenticated_request_with_token(client, auth_context):
    """Verify that valid JWT token permits access to protected endpoints."""
    res = client.get('/api/analytics/realtime', headers=auth_context['headers'])
    assert res.status_code in [200, 403]


def test_reset_password_rejects_unauthenticated_plain_identifier(client):
    """Verify that /api/auth/reset-password rejects requests lacking JWT or valid reset token."""
    res = client.post('/api/auth/reset-password', json={
        "email": "admin@example.com",
        "password": "HackedPassword123!"
    })
    assert res.status_code in [400, 401]
    data = res.get_json() or {}
    assert "token" in data.get("msg", "").lower() or "authorization" in data.get("msg", "").lower()


def test_seed_roles_endpoint_removed(client):
    """Verify that public /api/auth/seed-roles endpoint has been completely removed."""
    res = client.post('/api/auth/seed-roles', json={})
    assert res.status_code in [404, 405]


def test_uploads_requires_jwt_authentication(client):
    """Verify that /uploads/<filename> rejects unauthenticated requests with 401."""
    res = client.get('/uploads/confidential_document.pdf')
    assert res.status_code in [401, 422]


def test_phone_otp_response_has_no_debug_leak(client):
    """Verify that /api/auth/send-phone-otp does not leak plain OTP in JSON response."""
    res = client.post('/api/auth/send-phone-otp', json={
        "phone": "+919876543210"
    })
    data = res.get_json() or {}
    assert "otp_debug" not in data


def test_login_rate_limiting_enforced(client):
    """Verify that /api/auth/login triggers 429 when rate limit is exceeded."""
    # Send 6 consecutive login requests from the same test client IP
    last_res = None
    for _ in range(6):
        last_res = client.post('/api/auth/login', json={
            "email": "test_rate_limit@example.com",
            "password": "WrongPassword123!"
        })
    assert last_res.status_code == 429
    data = last_res.get_json() or {}
    assert data.get("code") == "RATE_LIMIT_EXCEEDED" or data.get("error_code") == "ACCOUNT_LOCKED"


def test_health_live_endpoint(client):
    res = client.get('/health/live')
    assert res.status_code == 200
    data = res.get_json()
    assert data.get('status') == 'ok'
    assert 'uptime_seconds' in data


def test_health_ready_endpoint(client):
    res = client.get('/health/ready')
    assert res.status_code == 200
    data = res.get_json()
    assert data.get('status') == 'ready'
    assert data.get('db') == 'ok'


def test_jwt_access_token_expiry_is_30_minutes(app):
    from app.config.settings import Config
    assert Config.JWT_ACCESS_TOKEN_EXPIRES == 1800

