import pytest


def test_api_routes_strict_no_cache(client):
    """Verify that all API endpoints enforce strict no-cache/no-store headers for security."""
    res = client.get('/api/health')
    assert res.status_code == 200
    cache_control = res.headers.get('Cache-Control', '')
    assert 'no-store' in cache_control
    assert 'no-cache' in cache_control
    assert 'must-revalidate' in cache_control
    assert 'max-age=0' in cache_control
    assert res.headers.get('Pragma') == 'no-cache'
    assert res.headers.get('Expires') == '-1'


def test_api_auth_endpoint_no_cache(client):
    """Verify that auth API endpoints never cache responses or credentials."""
    res = client.post('/api/auth/login', json={'username': 'invalid', 'password': 'wrong'})
    cache_control = res.headers.get('Cache-Control', '')
    assert 'no-store' in cache_control
    assert 'no-cache' in cache_control
    assert res.headers.get('Pragma') == 'no-cache'


def test_html_pages_revalidate_cache_control(client):
    """Verify that HTML pages use 'no-cache, must-revalidate' for conditional 304 revalidation."""
    res = client.get('/')
    cache_control = res.headers.get('Cache-Control', '')
    assert 'no-cache' in cache_control
    assert 'must-revalidate' in cache_control
    assert 'no-store' not in cache_control
    assert res.headers.get('Pragma') is None

    res_login = client.get('/auth/login.html')
    if res_login.status_code == 200:
        login_cache = res_login.headers.get('Cache-Control', '')
        assert 'no-cache' in login_cache
        assert 'must-revalidate' in login_cache
        assert 'no-store' not in login_cache
        assert res_login.headers.get('Pragma') is None


def test_hashed_dist_assets_immutable_cache(client):
    """Verify that hashed production assets return 1-year immutable caching."""
    res = client.get('/assets/dist/core.3ebcd984.min.css')
    if res.status_code == 200:
        cache_control = res.headers.get('Cache-Control', '')
        assert 'public' in cache_control
        assert 'max-age=31536000' in cache_control
        assert 'immutable' in cache_control
        assert res.headers.get('Pragma') is None
        assert res.headers.get('Expires') is None


def test_static_asset_extensions_caching(client):
    """Verify that static asset extensions under /assets/ return appropriate cache headers."""
    for asset_path in ['/assets/dist/core-bundle.min.js', '/assets/dist/manifest.json']:
        res = client.get(asset_path)
        if res.status_code == 200:
            cache_control = res.headers.get('Cache-Control', '')
            assert 'public' in cache_control
            assert res.headers.get('Pragma') is None
