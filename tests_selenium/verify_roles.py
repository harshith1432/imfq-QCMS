import time
from selenium.webdriver.common.by import By
from test_base import create_driver, TEST_USERS, BASE_URL

d = create_driver()
print("Testing standard btn.click() for 7 roles...")

for role, udata in TEST_USERS.items():
    d.get(f"{BASE_URL}/auth/login.html")
    time.sleep(1)
    user_inp = d.find_element(By.CSS_SELECTOR, "#username, input[type='text'], input[type='email']")
    pass_inp = d.find_element(By.CSS_SELECTOR, "#password, input[type='password']")
    btn = d.find_element(By.CSS_SELECTOR, "button[type='submit'], #loginBtn, .btn-primary")
    
    user_inp.clear()
    user_inp.send_keys(udata['email'])
    pass_inp.clear()
    pass_inp.send_keys(udata['pass'])
    btn.click()
    time.sleep(2.5)
    
    tok = d.execute_script("return sessionStorage.getItem('token') || localStorage.getItem('token') || localStorage.getItem('access_token') || sessionStorage.getItem('access_token')")
    print(f"{role} ({udata['email']}) -> Authenticated: {bool(tok)}, URL: {d.current_url}")

d.quit()
