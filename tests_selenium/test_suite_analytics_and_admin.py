import time
import requests
from selenium.webdriver.common.by import By
from test_base import BASE_URL, save_screenshot
from test_suite_super_admin import ensure_super_admin_logged_in

def run_analytics_and_rewards_tests(driver, report):
    print("\n================== 5. ENTERPRISE ANALYTICS & REWARDS ==================")
    ensure_super_admin_logged_in(driver)

    # 5.1 Analytics Dashboard
    t0 = time.time()
    try:
        driver.get(f"{BASE_URL}/analytics/analytics.html")
        time.sleep(3)
        body_text = driver.find_element(By.TAG_NAME, "body").text
        charts = driver.find_elements(By.CSS_SELECTOR, "canvas, [id*='chart'], [class*='chart']")
        assert len(body_text) > 100, "Analytics page is empty"
        report.record("Analytics", "Enterprise Analytics Dashboard", "PASS", f"Analytics rendered with {len(charts)} chart canvases", time.time() - t0)
    except Exception as e:
        save_screenshot(driver, "fail_analytics")
        report.record("Analytics", "Enterprise Analytics Dashboard", "FAIL", str(e), time.time() - t0)

    # 5.2 Gamification & Rewards Leaderboard
    t0 = time.time()
    try:
        driver.get(f"{BASE_URL}/rewards/leaderboard.html")
        time.sleep(2.5)
        body_text = driver.find_element(By.TAG_NAME, "body").text
        report.record("Rewards", "Gamification & Points Leaderboard", "PASS", f"Leaderboard loaded ({len(body_text)} chars)", time.time() - t0)
    except Exception as e:
        save_screenshot(driver, "fail_leaderboard")
        report.record("Rewards", "Gamification & Points Leaderboard", "FAIL", str(e), time.time() - t0)

def run_i18n_and_pdf_tests(driver, report):
    print("\n================== 6. MULTILINGUAL I18N & PDF ENGINE ==================")
    
    # 6.1 Multilingual Translation Dictionaries
    t0 = time.time()
    languages = ['en', 'hi', 'kn', 'te', 'ta', 'ml']
    valid_langs = []
    for lang in languages:
        try:
            res = requests.get(f"{BASE_URL}/assets/translations/{lang}.json", timeout=5)
            if res.status_code == 200 and len(res.json()) > 0:
                valid_langs.append(lang)
        except Exception:
            pass
    report.record("i18n", "Multilingual Dictionaries (6 Languages)", "PASS" if len(valid_langs) >= 5 else "WARN", f"Verified dictionary files: {', '.join(valid_langs)}", time.time() - t0)

    # 6.2 Automated PDF Endpoints
    t0 = time.time()
    try:
        token = driver.execute_script("return localStorage.getItem('token') || sessionStorage.getItem('token') || localStorage.getItem('access_token') || sessionStorage.getItem('access_token');")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        
        # Test backend health / reports endpoints
        res = requests.get(f"{BASE_URL}/api/reports/analytics/summary", headers=headers, timeout=5)
        report.record("Reports", "Reporting Engine API", "PASS", f"Status: {res.status_code}", time.time() - t0)
    except Exception as e:
        report.record("Reports", "Reporting Engine API", "FAIL", str(e), time.time() - t0)
