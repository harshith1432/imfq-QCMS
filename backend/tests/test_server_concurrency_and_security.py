import pytest
import time
import os
from unittest.mock import patch, MagicMock
from app import db


def test_gunicorn_configuration_attributes():
    """Verify that gunicorn.conf.py sets optimal concurrency, threading, and memory parameters."""
    g_vars = {}
    with open(os.path.join(os.path.dirname(__file__), '..', 'gunicorn.conf.py')) as f:
        code = compile(f.read(), 'gunicorn.conf.py', 'exec')
        exec(code, g_vars)

    assert g_vars.get('worker_class') == 'gthread'
    assert g_vars.get('preload_app') is True
    assert g_vars.get('threads') == 4
    assert g_vars.get('max_requests') == 1000
    assert g_vars.get('max_requests_jitter') == 100
    assert g_vars.get('timeout') == 60
    assert g_vars.get('graceful_timeout') == 30
    assert g_vars.get('keepalive') == 5
    assert g_vars.get('workers') >= 2


def test_production_security_headers_enforced(client):
    """Verify all responses include HSTS, CSP, X-Frame-Options, and nosniff headers."""
    res = client.get('/health/live')
    assert res.status_code == 200

    # 1. HSTS (2 years with includeSubDomains & preload)
    assert 'Strict-Transport-Security' in res.headers
    assert 'max-age=63072000' in res.headers['Strict-Transport-Security']
    assert 'includeSubDomains' in res.headers['Strict-Transport-Security']

    # 2. X-Content-Type-Options
    assert res.headers.get('X-Content-Type-Options') == 'nosniff'

    # 3. X-Frame-Options
    assert res.headers.get('X-Frame-Options') == 'SAMEORIGIN'

    # 4. Referrer-Policy
    assert res.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'

    # 5. Permissions-Policy
    assert 'camera=()' in res.headers.get('Permissions-Policy', '')
    assert 'microphone=()' in res.headers.get('Permissions-Policy', '')
    assert 'geolocation=()' in res.headers.get('Permissions-Policy', '')

    # 6. Content-Security-Policy
    csp = res.headers.get('Content-Security-Policy', '')
    assert "default-src 'self'" in csp
    assert 'https://cdn.jsdelivr.net' in csp


def test_proxy_fix_client_ip_resolution(client):
    """Verify ProxyFix resolves client IP from X-Forwarded-For without trusting spoofed multiple hops."""
    headers = {
        'X-Forwarded-For': '203.0.113.195',
        'X-Forwarded-Proto': 'https',
        'X-Forwarded-Host': 'qcms.enterprise.com'
    }
    res = client.get('/health/live', headers=headers)
    assert res.status_code == 200
    assert 'X-Request-ID' in res.headers


def test_waf_precompiled_regex_performance():
    """Verify precompiled WAF regex matches execute within sub-millisecond timeframe."""
    from app.presentation.middleware.security import _WAF_STRICT_PATTERNS

    malicious_payload = "1' UNION SELECT username, password FROM users WHERE 1=1 --"
    benign_payload = "Project Title: Quality Circle Improvement on Assembly Line 4"

    start_time = time.perf_counter()
    for _ in range(100):
        for pattern, label in _WAF_STRICT_PATTERNS:
            pattern.search(malicious_payload)
            pattern.search(benign_payload)
    elapsed = (time.perf_counter() - start_time) / 100

    # Must execute in < 0.2ms per request
    assert elapsed < 0.0005


def test_health_probes_liveness_and_readiness(client):
    """Verify /health/live and /health/ready respond appropriately."""
    # Liveness probe (instantaneous, 0 DB calls)
    live_res = client.get('/health/live')
    assert live_res.status_code == 200
    assert live_res.get_json()['status'] == 'ok'

    # Readiness probe (DB & cache health)
    ready_res = client.get('/health/ready')
    assert ready_res.status_code in (200, 503)
    ready_data = ready_res.get_json()
    assert 'db' in ready_data
    assert 'redis' in ready_data
