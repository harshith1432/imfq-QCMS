import requests
import json

BASE_URL = "http://127.0.0.1:5000/api"

def get_token(email, password):
    r = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    if r.status_code == 200:
        return r.json().get('access_token')
    else:
        print(f"Login failed: {r.status_code} - {r.text}")
    return None

def test_endpoints():
    token = get_token("admin@example.com", "admin123")
    if not token:
        # Try finding a user in the DB if the default fails
        print("Using fallback login search...")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # 1. Test Departments
    print("\n--- Testing Departments ---")
    r = requests.get(f"{BASE_URL}/admin/departments", headers=headers)
    print(f"GET /departments: {r.status_code}")
    
    r = requests.post(f"{BASE_URL}/admin/departments", headers=headers, json={"name": "Test Department"})
    print(f"POST /departments: {r.status_code}")
    if r.status_code == 201:
        dept_id = r.json().get('id')
        r = requests.put(f"{BASE_URL}/admin/departments/{dept_id}", headers=headers, json={"name": "Updated Department"})
        print(f"PUT /departments/{dept_id}: {r.status_code}")

    # 2. Test Org Settings
    print("\n--- Testing Org Settings ---")
    r = requests.get(f"{BASE_URL}/admin/org-settings", headers=headers)
    print(f"GET /org-settings: {r.status_code}")
    if r.status_code == 200:
        settings = r.json()
        print(f"Current Org: {settings.get('name')}")
        r = requests.put(f"{BASE_URL}/admin/org-settings", headers=headers, json={"name": settings.get('name') + " (Updated)"})
        print(f"PUT /org-settings: {r.status_code}")

    # 3. Test SOP Library
    print("\n--- Testing SOP Library ---")
    r = requests.get(f"{BASE_URL}/repository/sop-library", headers=headers)
    print(f"GET /repository/sop-library: {r.status_code}")

if __name__ == "__main__":
    test_endpoints()
