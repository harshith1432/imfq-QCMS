import requests
import json

BASE_URL = "http://127.0.0.1:5000/api"

def get_token(username, password):
    r = requests.post(f"{BASE_URL}/auth/login", json={"email": username, "password": password})
    if r.status_code == 200:
        return r.json().get('access_token')
    return None

def test_admin_access():
    print("Testing Admin Access...")
    # 1. Login as admin
    token = get_token("admin@example.com", "admin123")
    if not token:
        print("FAIL: Could not login as admin")
        return

    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Test Stats
    r = requests.get(f"{BASE_URL}/admin/stats", headers=headers)
    print(f"Stats Response ({r.status_code}): {r.json()}")
    
    # 3. Test Users
    r = requests.get(f"{BASE_URL}/admin/users", headers=headers)
    print(f"Users Count: {len(r.json())}")
    
    # 4. Test Audit Logs
    r = requests.get(f"{BASE_URL}/admin/audit-logs", headers=headers)
    print(f"Audit Logs Count: {len(r.json())}")

def test_non_admin_access():
    print("\nTesting Non-Admin Access (Expecting 403)...")
    token = get_token("member@example.com", "member123")
    if not token:
        print("FAIL: Could not login as member")
        return

    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{BASE_URL}/admin/stats", headers=headers)
    print(f"Stats Response ({r.status_code}): {r.json().get('message')}")

if __name__ == "__main__":
    test_admin_access()
    test_non_admin_access()
