import time
from selenium.webdriver.common.by import By
from test_base import BASE_URL, save_screenshot
from test_suite_super_admin import ensure_super_admin_logged_in

def run_dashboard_tests(driver, report):
    print("\n================== 3. ROLE-BASED DASHBOARD TESTS ==================")
    ensure_super_admin_logged_in(driver)

    dashboards = [
        ("Admin Dashboard", "/dashboard/dashboard-admin.html", "Org Admin metrics and operational summary"),
        ("CEO Dashboard", "/dashboard/dashboard-ceo.html", "Executive KPIs, ROI and organization-wide metrics"),
        ("Facilitator Dashboard", "/dashboard/dashboard-facilitator.html", "Stage coaching and facilitator guidance"),
        ("Reviewer Dashboard", "/dashboard/dashboard-reviewer.html", "Stage approvals, gates, and sign-offs"),
        ("Team Member Dashboard", "/dashboard/dashboard-team-member.html", "My tasks, active circles and contributions"),
    ]

    for name, path, desc in dashboards:
        t0 = time.time()
        try:
            driver.get(f"{BASE_URL}{path}")
            time.sleep(2.5)
            body_text = driver.find_element(By.TAG_NAME, "body").text
            cards = driver.find_elements(By.CSS_SELECTOR, ".card, .glass-card, .metric-card, [class*='card']")
            charts = driver.find_elements(By.CSS_SELECTOR, "canvas, [id*='chart'], [class*='chart']")
            
            assert len(body_text) > 80, f"{name} text content too short"
            report.record("Dashboards", f"{name} View", "PASS", f"Loaded with {len(cards)} cards & {len(charts)} chart widgets. ({desc})", time.time() - t0)
        except Exception as e:
            save_screenshot(driver, f"fail_{name.lower().replace(' ', '_')}")
            report.record("Dashboards", f"{name} View", "FAIL", str(e), time.time() - t0)
