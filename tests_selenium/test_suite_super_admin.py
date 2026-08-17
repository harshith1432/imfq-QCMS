import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from test_base import BASE_URL, save_screenshot

def ensure_super_admin_logged_in(driver):
    # Check if already authenticated
    try:
        token = driver.execute_script("return localStorage.getItem('token') || sessionStorage.getItem('token') || localStorage.getItem('access_token') || sessionStorage.getItem('access_token');")
        if token:
            return
    except Exception:
        pass

    driver.get(f"{BASE_URL}/auth/login.html")
    time.sleep(1.5)
    user_inp = driver.find_elements(By.CSS_SELECTOR, "#username, input[type='text'], input[type='email']")
    pass_inp = driver.find_elements(By.CSS_SELECTOR, "#password, input[type='password']")
    btn = driver.find_elements(By.CSS_SELECTOR, "button[type='submit'], #login-btn, .btn-primary")
    
    if user_inp and pass_inp and btn:
        user_inp[0].clear()
        user_inp[0].send_keys("harshithkd6@gmail.com")
        pass_inp[0].clear()
        pass_inp[0].send_keys("123456")
        btn[0].click()
        time.sleep(2.5)

def run_super_admin_tests(driver, report):
    print("\n================== 2. SUPER ADMIN & GOVERNANCE TESTS ==================", flush=True)
    ensure_super_admin_logged_in(driver)

    # 2.1 Super Admin Dashboard
    t0 = time.time()
    try:
        driver.get(f"{BASE_URL}/admin/super-admin.html")
        time.sleep(2.5)
        body_text = driver.find_element(By.TAG_NAME, "body").text
        assert len(body_text) > 100, "Super admin page is empty"
        report.record("SuperAdmin", "Super Admin Portal Load", "PASS", f"Super Admin UI loaded ({len(body_text)} chars)", time.time() - t0)
    except Exception as e:
        save_screenshot(driver, "fail_super_admin_portal")
        report.record("SuperAdmin", "Super Admin Portal Load", "FAIL", str(e), time.time() - t0)

    # 2.2 User Management Page
    t0 = time.time()
    try:
        driver.get(f"{BASE_URL}/admin/users.html")
        time.sleep(2.5)
        body_text = driver.find_element(By.TAG_NAME, "body").text
        tables = driver.find_elements(By.TAG_NAME, "table")
        buttons = driver.find_elements(By.TAG_NAME, "button")
        assert len(body_text) > 100, "Users page is empty"
        report.record("SuperAdmin", "User Management Interface", "PASS", f"Rendered with {len(tables)} tables, {len(buttons)} controls", time.time() - t0)
    except Exception as e:
        save_screenshot(driver, "fail_admin_users")
        report.record("SuperAdmin", "User Management Interface", "FAIL", str(e), time.time() - t0)

    # 2.3 Plant Management Page
    t0 = time.time()
    try:
        driver.get(f"{BASE_URL}/admin/plants.html")
        time.sleep(2)
        body_text = driver.find_element(By.TAG_NAME, "body").text
        report.record("SuperAdmin", "Plant Hierarchy Management", "PASS", f"Plant manager loaded ({len(body_text)} chars)", time.time() - t0)
    except Exception as e:
        save_screenshot(driver, "fail_admin_plants")
        report.record("SuperAdmin", "Plant Hierarchy Management", "FAIL", str(e), time.time() - t0)

    # 2.4 Department Management Page
    t0 = time.time()
    try:
        driver.get(f"{BASE_URL}/admin/departments.html")
        time.sleep(2)
        body_text = driver.find_element(By.TAG_NAME, "body").text
        report.record("SuperAdmin", "Department Management", "PASS", f"Departments view loaded ({len(body_text)} chars)", time.time() - t0)
    except Exception as e:
        save_screenshot(driver, "fail_admin_departments")
        report.record("SuperAdmin", "Department Management", "FAIL", str(e), time.time() - t0)

    # 2.5 Subscriptions & Pricing Management
    t0 = time.time()
    try:
        driver.get(f"{BASE_URL}/admin/subscriptions.html")
        time.sleep(2)
        body_text = driver.find_element(By.TAG_NAME, "body").text
        report.record("SuperAdmin", "Subscription & Plans Governance", "PASS", f"Subscription manager loaded ({len(body_text)} chars)", time.time() - t0)
    except Exception as e:
        save_screenshot(driver, "fail_admin_subscriptions")
        report.record("SuperAdmin", "Subscription & Plans Governance", "FAIL", str(e), time.time() - t0)

    # 2.6 Global Platform Settings & Document Branding
    t0 = time.time()
    try:
        driver.get(f"{BASE_URL}/admin/settings.html")
        time.sleep(2.5)
        body_text = driver.find_element(By.TAG_NAME, "body").text
        inputs = driver.find_elements(By.TAG_NAME, "input")
        report.record("SuperAdmin", "Platform Settings & Document Branding", "PASS", f"Settings view loaded with {len(inputs)} configuration fields", time.time() - t0)
    except Exception as e:
        save_screenshot(driver, "fail_admin_settings")
        report.record("SuperAdmin", "Platform Settings & Document Branding", "FAIL", str(e), time.time() - t0)

    # 2.7 Compliance Audit Trail & Activity Logs
    t0 = time.time()
    try:
        driver.get(f"{BASE_URL}/admin/audit-logs.html")
        time.sleep(2.5)
        body_text = driver.find_element(By.TAG_NAME, "body").text
        report.record("SuperAdmin", "Compliance Audit Telemetry Logs", "PASS", f"Audit logs view rendered ({len(body_text)} chars)", time.time() - t0)
    except Exception as e:
        save_screenshot(driver, "fail_admin_audit_logs")
        report.record("SuperAdmin", "Compliance Audit Telemetry Logs", "FAIL", str(e), time.time() - t0)

    # 2.8 Audit Queue
    t0 = time.time()
    try:
        driver.get(f"{BASE_URL}/admin/audit-queue.html")
        time.sleep(2)
        body_text = driver.find_element(By.TAG_NAME, "body").text
        report.record("SuperAdmin", "Audit Queue & Approval Pipeline", "PASS", f"Audit queue rendered ({len(body_text)} chars)", time.time() - t0)
    except Exception as e:
        save_screenshot(driver, "fail_admin_audit_queue")
        report.record("SuperAdmin", "Audit Queue & Approval Pipeline", "FAIL", str(e), time.time() - t0)

    # 2.9 Developer Portal & API Keys
    t0 = time.time()
    try:
        driver.get(f"{BASE_URL}/admin/developer-portal.html")
        time.sleep(2)
        body_text = driver.find_element(By.TAG_NAME, "body").text
        report.record("SuperAdmin", "Developer Portal & REST APIs", "PASS", f"Developer portal loaded ({len(body_text)} chars)", time.time() - t0)
    except Exception as e:
        save_screenshot(driver, "fail_admin_dev_portal")
        report.record("SuperAdmin", "Developer Portal & REST APIs", "FAIL", str(e), time.time() - t0)

    # 2.10 SOP Masters Repository
    t0 = time.time()
    try:
        driver.get(f"{BASE_URL}/admin/sop-masters.html")
        time.sleep(2)
        body_text = driver.find_element(By.TAG_NAME, "body").text
        report.record("SuperAdmin", "SOP Masters Management", "PASS", f"SOP master repository loaded ({len(body_text)} chars)", time.time() - t0)
    except Exception as e:
        save_screenshot(driver, "fail_admin_sop_masters")
        report.record("SuperAdmin", "SOP Masters Management", "FAIL", str(e), time.time() - t0)

    # 2.11 Stage Template Customizer
    t0 = time.time()
    try:
        driver.get(f"{BASE_URL}/admin/stage-template.html")
        time.sleep(2)
        body_text = driver.find_element(By.TAG_NAME, "body").text
        report.record("SuperAdmin", "Stage Template Customization", "PASS", f"Stage template builder rendered ({len(body_text)} chars)", time.time() - t0)
    except Exception as e:
        save_screenshot(driver, "fail_admin_stage_template")
        report.record("SuperAdmin", "Stage Template Customization", "FAIL", str(e), time.time() - t0)
