"""
QCMS Post-Deployment Automated Smoke Test Suite
===============================================
Validates that the deployed instance is fully operational after container build,
database migration, and service launch.
"""

import sys
import time
import requests
import json

DEFAULT_HOST = "http://127.0.0.1:5000"

def check_endpoint(name, url, expected_statuses=(200,), timeout=10):
    start = time.time()
    try:
        if not (url.startswith('https://') or url.startswith('http://')):
            print(f"  [FAIL] {name} ({url}) -> Invalid protocol")
            return False
        resp = requests.get(
            url,
            headers={"User-Agent": "QCMS-SmokeTest/1.0", "Accept": "application/json"},
            timeout=timeout
        )
        duration_ms = round((time.time() - start) * 1000, 2)
        if resp.status_code in expected_statuses:
            print(f"  [PASS] {name} ({url}) -> HTTP {resp.status_code} in {duration_ms}ms")
            return True
        else:
            print(f"  [FAIL] {name} ({url}) -> Unexpected HTTP {resp.status_code} (Expected: {expected_statuses})")
            return False
    except Exception as e:
        duration_ms = round((time.time() - start) * 1000, 2)
        print(f"  [FAIL] {name} ({url}) -> Connection Error: {e} in {duration_ms}ms")
        return False

def run_smoke_tests(base_url=DEFAULT_HOST):
    print("=" * 65)
    print(f" [QCMS] Executing Production Smoke Test Suite against {base_url}")
    print("=" * 65)
    
    tests = [
        ("Liveness Health Probe", f"{base_url}/health/live", (200,)),
        ("Readiness DB Probe", f"{base_url}/health/ready", (200,)),
        ("Platform Maintenance Status", f"{base_url}/api/auth/maintenance-status", (200,)),
        ("Login Configuration API", f"{base_url}/api/auth/login-config", (200,)),
        ("Registration Availability Check", f"{base_url}/api/auth/registration-status", (200,)),
    ]
    
    passed = 0
    total = len(tests)
    
    for name, url, expected in tests:
        if check_endpoint(name, url, expected):
            passed += 1
            
    print("-" * 65)
    print(f" Results: {passed}/{total} checks passed ({round(passed/total*100, 1)}%)")
    print("=" * 65)
    
    if passed == total:
        print(" ALL SMOKE TESTS PASSED! DEPLOYMENT VERIFIED.")
        return 0
    else:
        print(f" {total - passed} SMOKE TEST(S) FAILED. CHECK SYSTEM LOGS.")
        return 1

if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_HOST
    exit_code = run_smoke_tests(host)
    sys.exit(exit_code)
