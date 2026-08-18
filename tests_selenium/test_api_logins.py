import requests

base = 'http://127.0.0.1:5000'
users = [
    ('SuperAdmin', 'harshithkd6@gmail.com', '123456'),
    ('Admin', 'gelala@fxzig.com', 'Himnish@123'),
    ('Reviewer', 'sameer.kumar57@example.com', 'Welcome@123'),
    ('Facilitator', 'priti.trivedi120@example.com', 'Welcome@123'),
    ('TeamMember1', 'nitin.murthy9@example.com', 'Welcome@123'),
    ('CEO', 'Ajay@gmail.com', 'Welcome@123'),
    ('TeamMember2', 'kavya.raghavan174@example.com', 'Welcome@123')
]

for role, email, pwd in users:
    r = requests.post(f'{base}/api/auth/login', json={'username': email, 'password': pwd})
    data = r.json()
    print(f"{role} ({email}) -> Status: {r.status_code}, Role: {data.get('role')}, Token: {bool(data.get('access_token'))}")
