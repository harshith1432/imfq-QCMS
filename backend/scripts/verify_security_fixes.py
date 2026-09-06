import os
import sys
import json
import re
import time

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.infrastructure.database.models.models import User, Role, Organization, AuditLog
from flask_jwt_extended import decode_token, create_access_token

def run_tests():
    print("=" * 70)
    print("OCTAQUBE ENTERPRISE QCMS - EXTENSIVE SECURITY VERIFICATION SUITE")
    print("=" * 70)

    app = create_app()
    app.config['TESTING'] = True
    client = app.test_client()

    with app.app_context():
        # Ensure a test user exists for testing
        test_user = User.query.filter_by(username="test_sec_user").first()
        role = Role.query.filter_by(name="Admin").first()
        org = Organization.query.first()
        from app import bcrypt
        if not test_user:
            test_user = User(
                username="test_sec_user",
                email="test_sec_user@example.com",
                phone="9876543210",
                hashed_password=bcrypt.generate_password_hash("ValidPass123!").decode('utf-8'),
                role_id=role.id if role else 1,
                org_id=org.id if org else 1,
                is_active=True,
                is_verified=True,
                status="Active"
            )
            db.session.add(test_user)
            db.session.commit()
            print(f"[SETUP] Created test user: {test_user.username}")
        else:
            print(f"[SETUP] Using existing test user: {test_user.username}")

        # Ensure an audit log with an IP address exists for testing
        sample_log = AuditLog.query.filter(AuditLog.action == "TEST_SECURITY_AUDIT").first()
        if not sample_log:
            sample_log = AuditLog(
                user_id=test_user.id,
                org_id=test_user.org_id,
                action="TEST_SECURITY_AUDIT",
                target_table="users",
                target_id=test_user.id,
                details={"username": "test_sec_user", "ip": "117.232.44.133", "note": "Connection from 117.232.44.133"},
                ip_address="117.232.44.133"
            )
            db.session.add(sample_log)
            db.session.commit()

        admin_token = create_access_token(
            identity=str(test_user.id),
            additional_claims={"session_id": "TEST-SESS-001", "org_id": test_user.org_id, "role": "Admin"}
        )

    failures = []

    # -------------------------------------------------------------------------
    # TEST 1: BOLA-01 & BOLA-02: Unauthenticated Admin Endpoints
    # -------------------------------------------------------------------------
    print("\n[TEST 1] BOLA-01 & BOLA-02: Unauthenticated Admin Access")
    admin_endpoints = [
        "/api/admin/users",
        "/api/admin/plants",
        "/api/admin/audit-logs",
        "/api/admin/audit/logs"
    ]

    for ep in admin_endpoints:
        # Case A: Anonymous request (no token, no cookies)
        res = client.get(ep)
        if res.status_code == 401:
            print(f"  PASS: Anonymous GET {ep} -> 401 Unauthorized")
        else:
            print(f"  FAIL: Anonymous GET {ep} -> {res.status_code} (expected 401)")
            failures.append(f"Anonymous GET {ep} returned {res.status_code}")

        # Case B: Request with access_token_cookie only (ambient cookie) - must still be 401
        client.set_cookie('access_token_cookie', 'fake.jwt.token')
        res = client.get(ep)
        if res.status_code == 401:
            print(f"  PASS: Cookie-only GET {ep} -> 401 (Headers-only JWT enforced)")
        else:
            print(f"  FAIL: Cookie-only GET {ep} -> {res.status_code} (expected 401)")
            failures.append(f"Cookie-only GET {ep} returned {res.status_code}")

    # -------------------------------------------------------------------------
    # TEST 2: Data Masking: User Email & Phone PII in User List
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Data Masking: User Emails & Phone in /api/admin/users")
    res_users = client.get('/api/admin/users', headers={"Authorization": f"Bearer {admin_token}"})
    if res_users.status_code == 200:
        users_body = res_users.get_data(as_text=True)
        if "test_sec_user@example.com" in users_body:
            print("  FAIL: Plaintext email test_sec_user@example.com found in user list")
            failures.append("Plaintext email exposed in /api/admin/users")
        else:
            print("  PASS: Plaintext email is masked/redacted in /api/admin/users response")

        users_json = res_users.get_json()
        users_items = users_json if isinstance(users_json, list) else users_json.get('items', [])
        masked_found = any('***' in (u.get('email') or '') for u in users_items)
        if masked_found:
            print("  PASS: Email is properly masked (e.g. te***r@example.com)")
        else:
            print("  INFO: No emails or all masked")
    else:
        print(f"  FAIL: GET /api/admin/users returned {res_users.status_code}")
        failures.append(f"GET /api/admin/users returned {res_users.status_code}")

    # -------------------------------------------------------------------------
    # TEST 3: Data Masking: IP Addresses in Audit Logs
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Data Masking: IP Addresses in /api/admin/audit-logs")
    res_audit = client.get('/api/admin/audit-logs', headers={"Authorization": f"Bearer {admin_token}"})
    if res_audit.status_code == 200:
        audit_body = res_audit.get_data(as_text=True)
        # Search for raw IPv4 pattern
        raw_ips = re.findall(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b', audit_body)
        raw_external_ips = [ip for ip in raw_ips if ip not in ('127.0.0.1', '0.0.0.0')]
        if raw_external_ips:
            print(f"  FAIL: Raw IP addresses exposed in audit logs: {raw_external_ips[:3]}")
            failures.append(f"Raw IP addresses exposed in /api/admin/audit-logs: {raw_external_ips[:3]}")
        else:
            print("  PASS: All raw IP addresses are masked or omitted in /api/admin/audit-logs response")
    else:
        print(f"  FAIL: GET /api/admin/audit-logs returned {res_audit.status_code}")
        failures.append(f"GET /api/admin/audit-logs returned {res_audit.status_code}")

    # -------------------------------------------------------------------------
    # TEST 4: AUTH-01 & INFO-01: Forgot Password Enumeration & Data Exposure
    # -------------------------------------------------------------------------
    print("\n[TEST 4] AUTH-01 & INFO-01: Forgot Password Enumeration & Data Exposure")
    res_exist = client.post('/api/auth/forgot-password', json={"identifier": "test_sec_user@example.com"})
    data_exist = res_exist.get_json() or {}

    res_nonexist = client.post('/api/auth/forgot-password', json={"identifier": "nonexistent_fake_email_9999@example.com"})
    data_nonexist = res_nonexist.get_json() or {}

    if res_exist.status_code == 200 and res_nonexist.status_code == 200:
        print("  PASS: Both existing and non-existent identifiers return 200 OK")
    else:
        print(f"  FAIL: Status codes: existing={res_exist.status_code}, non-existent={res_nonexist.status_code}")
        failures.append("Forgot password status codes do not match 200")

    if data_exist.get('msg') == data_nonexist.get('msg'):
        print(f"  PASS: Uniform message returned: \"{data_exist.get('msg')}\"")
    else:
        print(f"  FAIL: Differing messages: '{data_exist.get('msg')}' vs '{data_nonexist.get('msg')}'")
        failures.append("Forgot password messages leak user existence")

    sensitive_keys = ['user_id', 'masked_email', 'masked_phone', 'has_email', 'has_phone']
    leaked = [k for k in sensitive_keys if k in data_exist]
    if not leaked:
        print("  PASS: INFO-01: No sensitive data (user_id, masked_email, has_email) in response")
    else:
        print(f"  FAIL: INFO-01: Leaked keys: {leaked}")
        failures.append(f"Forgot password leaks keys: {leaked}")

    # -------------------------------------------------------------------------
    # TEST 5: AUTH-02: Rate-Limit Headers on Failed Login (401 & 429)
    # -------------------------------------------------------------------------
    print("\n[TEST 5] AUTH-02: Rate-Limit Headers on Failed Login")
    from app.presentation.middleware.security import clear_login_lockout
    clear_login_lockout("test_rate_user")

    # Wrong password attempt 1 -> must return 401 with X-RateLimit headers
    res_fail1 = client.post('/api/auth/login', json={
        "username": "test_rate_user",
        "password": "WrongPassword1!"
    })
    
    if res_fail1.status_code == 401:
        rl_limit = res_fail1.headers.get('X-RateLimit-Limit')
        rl_rem = res_fail1.headers.get('X-RateLimit-Remaining')
        if rl_limit == '5' and rl_rem is not None:
            print(f"  PASS: 401 response has X-RateLimit-Limit={rl_limit} and X-RateLimit-Remaining={rl_rem}")
        else:
            print(f"  FAIL: 401 response missing X-RateLimit headers: Limit={rl_limit}, Remaining={rl_rem}")
            failures.append("401 response missing X-RateLimit headers")
    else:
        print(f"  FAIL: Expected 401 on failed password, got {res_fail1.status_code}")
        failures.append(f"Expected 401 on failed password, got {res_fail1.status_code}")

    # Attempts 2, 3, 4, 5 to trigger 429
    for i in range(2, 6):
        client.post('/api/auth/login', json={"username": "test_rate_user", "password": f"WrongPassword{i}!"})

    # Attempt 6 -> must return 429
    res_lock = client.post('/api/auth/login', json={"username": "test_rate_user", "password": "WrongPassword6!"})
    if res_lock.status_code == 429:
        retry_after = res_lock.headers.get('Retry-After')
        if retry_after and int(retry_after) > 0:
            print(f"  PASS: 429 response has Retry-After: {retry_after}s")
        else:
            print(f"  FAIL: 429 response missing Retry-After header: {retry_after}")
            failures.append("429 response missing Retry-After header")
    else:
        print(f"  FAIL: Expected 429 lockout, got {res_lock.status_code}")
        failures.append(f"Expected 429 lockout, got {res_lock.status_code}")

    # Now test: Unknown email/user in the same test sequence -> MUST return 401 (NOT 429)
    res_unknown = client.post('/api/auth/login', json={
        "username": "unknown_different_user_99999",
        "password": "WrongPassword1!"
    })
    if res_unknown.status_code == 401:
        print("  PASS: Unknown user returns 401 (not locked out by earlier user brute force)")
    else:
        print(f"  FAIL: Unknown user returned {res_unknown.status_code} (expected 401)")
        failures.append(f"Unknown user returned {res_unknown.status_code} instead of 401")

    clear_login_lockout("test_rate_user")

    # -------------------------------------------------------------------------
    # TEST 6: JWT-01: Token Expiry (30 mins) & Refresh Mechanism
    # -------------------------------------------------------------------------
    print("\n[TEST 6] JWT-01: Token Expiry (30 mins) & Refresh Mechanism")
    res_login = client.post('/api/auth/login', json={
        "username": "test_sec_user",
        "password": "ValidPass123!"
    })

    if res_login.status_code == 200:
        login_data = res_login.get_json() or {}
        access_token = login_data.get('access_token')
        refresh_token = login_data.get('refresh_token')
        expires_in = login_data.get('expires_in')

        if access_token and refresh_token:
            print("  PASS: Login returned both access_token and refresh_token")
        else:
            print("  FAIL: Login did not return both tokens")
            failures.append("Login missing access_token or refresh_token")

        with app.app_context():
            decoded = decode_token(access_token)
            ttl = decoded['exp'] - decoded['iat']
            if ttl <= 1800:
                print(f"  PASS: Decoded access token TTL is {ttl}s (<= 30 mins / 1800s)")
            else:
                print(f"  FAIL: Decoded access token TTL is {ttl}s (expected <= 1800s)")
                failures.append(f"Access token TTL {ttl}s exceeds 1800s")

        res_refresh = client.post('/api/auth/refresh', headers={
            "Authorization": f"Bearer {refresh_token}"
        })
        if res_refresh.status_code == 200:
            print("  PASS: POST /api/auth/refresh successfully exchanged refresh token for new access_token")
        else:
            print(f"  FAIL: POST /api/auth/refresh returned {res_refresh.status_code}")
            failures.append(f"POST /api/auth/refresh failed with status {res_refresh.status_code}")

    # -------------------------------------------------------------------------
    # TEST 7: Invalid Token Returns 401 (Not 422)
    # -------------------------------------------------------------------------
    print("\n[TEST 7] Invalid Token Returns 401 Unauthorized (Not 422)")
    res_bad_jwt = client.get('/api/admin/users', headers={
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature"
    })
    if res_bad_jwt.status_code == 401:
        print(f"  PASS: Invalid token returned 401 Unauthorized (msg: {res_bad_jwt.get_json().get('msg')})")
    else:
        print(f"  FAIL: Invalid token returned {res_bad_jwt.status_code} (expected 401)")
        failures.append(f"Invalid token returned {res_bad_jwt.status_code} instead of 401")

    # -------------------------------------------------------------------------
    # TEST 8: Security Headers: CSP Does Not Contain 'unsafe-eval'
    # -------------------------------------------------------------------------
    print("\n[TEST 8] Security Headers: CSP unsafe-eval check")
    res_head = client.get('/api/health/live')
    csp_header = res_head.headers.get('Content-Security-Policy', '')
    if 'unsafe-eval' not in csp_header:
        print("  PASS: Content-Security-Policy header does NOT contain 'unsafe-eval'")
    else:
        print(f"  FAIL: Content-Security-Policy still contains 'unsafe-eval': {csp_header}")
        failures.append("Content-Security-Policy contains 'unsafe-eval'")

    # -------------------------------------------------------------------------
    # SUMMARY
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    if not failures:
        print("ALL SECURITY AND POSTMAN COMPLIANCE CHECKS PASSED!")
        print("=" * 70)
        return 0
    else:
        print(f"FAILED CHECKS ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        print("=" * 70)
        return 1

if __name__ == '__main__':
    sys.exit(run_tests())
