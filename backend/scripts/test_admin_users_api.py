import requests
import json

def main():
    # Login as admin
    login_url = "http://127.0.0.1:5000/api/auth/login"
    login_payload = {
        "identifier": "harshithkd6@gmail.com",
        "password": "123456"
    }

    try:
        res = requests.post(login_url, json=login_payload)
        if res.status_code == 200:
            token = res.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            users_res = requests.get("http://127.0.0.1:5000/api/admin/users", headers=headers)
            print("USERS API RESPONSE:")
            print(json.dumps(users_res.json()[:2], indent=2))
        else:
            print("LOGIN FAILED:", res.text)
    except Exception as e:
        print("Error connecting to server:", e)

if __name__ == '__main__':
    main()
