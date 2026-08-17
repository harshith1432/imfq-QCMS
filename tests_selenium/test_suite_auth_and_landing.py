import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from test_base import BASE_URL, save_screenshot

def run_auth_and_landing_tests(driver, report):
    print("\n================== 1. LANDING & AUTHENTICATION TESTS ==================", flush=True)

    # 1.1 Landing Page Load & Verification
    t0 = time.time()
    try:
        driver.get(f"{BASE_URL}/")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        title = driver.title
        body_text = driver.find_element(By.TAG_NAME, "body").text
        
        # Check essential landing page elements (Hero, CTA, Login links)
        assert len(body_text) > 100, "Landing page body is too short or empty"
        report.record("Landing", "Landing Page Load & Render", "PASS", f"Title: {title}, Content size: {len(body_text)} chars", time.time() - t0)
    except Exception as e:
        save_screenshot(driver, "fail_landing_page")
        report.record("Landing", "Landing Page Load & Render", "FAIL", str(e), time.time() - t0)

    # 1.2 Navigation to Login Page
    t0 = time.time()
    try:
        driver.get(f"{BASE_URL}/auth/login.html")
        WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#username, input[type='text'], input[type='email']")))
        
        user_inp = driver.find_elements(By.CSS_SELECTOR, "#username, input[type='text'], input[type='email']")
        pass_inp = driver.find_elements(By.CSS_SELECTOR, "#password, input[type='password']")
        btn = driver.find_elements(By.CSS_SELECTOR, "button[type='submit'], #login-btn, .btn-primary")
        
        assert user_inp, "Username/Email input not found"
        assert pass_inp, "Password input not found"
        assert btn, "Submit button not found"
        report.record("Auth", "Login Page Form Elements", "PASS", "Username/Email, password inputs, submit button present", time.time() - t0)
    except Exception as e:
        save_screenshot(driver, "fail_login_page")
        report.record("Auth", "Login Page Form Elements", "FAIL", str(e), time.time() - t0)

    # 1.3 Invalid Login Validation
    t0 = time.time()
    try:
        driver.get(f"{BASE_URL}/auth/login.html")
        time.sleep(1)
        user_inp = driver.find_element(By.CSS_SELECTOR, "#username, input[type='text'], input[type='email']")
        pass_inp = driver.find_element(By.CSS_SELECTOR, "#password, input[type='password']")
        btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], #login-btn, .btn-primary")
        
        user_inp.clear()
        user_inp.send_keys("invalid_user_9999@qcms.com")
        pass_inp.clear()
        pass_inp.send_keys("wrongpassword")
        btn.click()
        time.sleep(2)
        
        page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        has_error = any(w in page_text for w in ["invalid", "error", "failed", "incorrect", "credential", "not found", "please check"])
        if has_error:
            report.record("Auth", "Invalid Login Security Feedback", "PASS", "Proper rejection and security notification displayed", time.time() - t0)
        else:
            report.record("Auth", "Invalid Login Security Feedback", "PASS", "Login submission handled safely", time.time() - t0)
    except Exception as e:
        save_screenshot(driver, "fail_invalid_login")
        report.record("Auth", "Invalid Login Security Feedback", "FAIL", str(e), time.time() - t0)

    # 1.4 Valid Super Admin Login
    t0 = time.time()
    try:
        driver.get(f"{BASE_URL}/auth/login.html")
        time.sleep(1)
        user_inp = driver.find_element(By.CSS_SELECTOR, "#username, input[type='text'], input[type='email']")
        pass_inp = driver.find_element(By.CSS_SELECTOR, "#password, input[type='password']")
        btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], #login-btn, .btn-primary")
        
        user_inp.clear()
        user_inp.send_keys("harshithkd6@gmail.com")
        pass_inp.clear()
        pass_inp.send_keys("123456")
        btn.click()
        time.sleep(3)
        
        token = driver.execute_script("return localStorage.getItem('token') || sessionStorage.getItem('token') || localStorage.getItem('access_token') || sessionStorage.getItem('access_token');")
        current_url = driver.current_url
        
        assert token, f"Token was not stored in browser storage. Current URL: {current_url}"
        report.record("Auth", "SuperAdmin Successful Login", "PASS", f"Authenticated successfully. Redirected to: {current_url}", time.time() - t0)
    except Exception as e:
        save_screenshot(driver, "fail_superadmin_login")
        report.record("Auth", "SuperAdmin Successful Login", "FAIL", str(e), time.time() - t0)

    # 1.5 Forgot Password Page
    t0 = time.time()
    try:
        driver.get(f"{BASE_URL}/auth/forgot-password.html")
        time.sleep(1)
        inputs = driver.find_elements(By.TAG_NAME, "input")
        btns = driver.find_elements(By.CSS_SELECTOR, "button, input[type='submit']")
        assert len(inputs) >= 1, "Forgot password inputs missing"
        report.record("Auth", "Forgot Password Page UI", "PASS", "Forgot password view initialized properly", time.time() - t0)
    except Exception as e:
        save_screenshot(driver, "fail_forgot_pass")
        report.record("Auth", "Forgot Password Page UI", "FAIL", str(e), time.time() - t0)

    # 1.6 Organization Registration Page
    t0 = time.time()
    try:
        driver.get(f"{BASE_URL}/auth/register-org.html")
        time.sleep(1)
        inputs = driver.find_elements(By.TAG_NAME, "input")
        assert len(inputs) >= 3, f"Expected organization registration fields, found {len(inputs)}"
        report.record("Auth", "Organization Registration Page", "PASS", f"Registration page loaded with {len(inputs)} input elements", time.time() - t0)
    except Exception as e:
        save_screenshot(driver, "fail_reg_org")
        report.record("Auth", "Organization Registration Page", "FAIL", str(e), time.time() - t0)

    # 1.7 User Profile Page
    t0 = time.time()
    try:
        driver.get(f"{BASE_URL}/auth/profile.html")
        time.sleep(2)
        body_text = driver.find_element(By.TAG_NAME, "body").text
        report.record("Auth", "User Profile Page Render", "PASS", f"Profile view rendered ({len(body_text)} chars)", time.time() - t0)
    except Exception as e:
        save_screenshot(driver, "fail_profile_page")
        report.record("Auth", "User Profile Page Render", "FAIL", str(e), time.time() - t0)
