"""
Base Test Framework and Utilities for QCMS Deep Selenium Testing
"""

import os
import sys
import time
import json
import traceback
from datetime import datetime

# Ensure stdout handles UTF-8 smoothly on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

BASE_URL = "http://127.0.0.1:5000"
SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# User credentials provided
TEST_USERS = {
    "SuperAdmin": {"email": "harshithkd6@gmail.com", "pass": "123456", "role": "SuperAdmin"},
    "Admin": {"email": "gelala@fxzig.com", "pass": "Himnish@123", "role": "Admin"},
    "Reviewer": {"email": "sameer.kumar57@example.com", "pass": "Welcome@123", "role": "Reviewer"},
    "Facilitator": {"email": "priti.trivedi120@example.com", "pass": "Welcome@123", "role": "Facilitator"},
    "TeamMember1": {"email": "nitin.murthy9@example.com", "pass": "Welcome@123", "role": "Team Member"},
    "CEO": {"email": "Ajay@gmail.com", "pass": "Welcome@123", "role": "CEO"},
    "TeamMember2": {"email": "kavya.raghavan174@example.com", "pass": "Welcome@123", "role": "Team Member"},
}

class DetailedTestReport:
    def __init__(self):
        self.results = []
        self.start_time = time.time()
        self.category_counts = {}

    def record(self, category, name, route, action, expected, actual, status, screenshot_path=None, duration=0.0, notes=""):
        res = {
            "id": len(self.results) + 1,
            "category": category,
            "name": name,
            "route": route,
            "action": action,
            "expected": expected,
            "actual": actual,
            "status": status,  # PASS, FAIL, WARN, BLOCKED
            "screenshot": screenshot_path or "",
            "duration": round(duration, 3),
            "notes": notes,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.results.append(res)
        self.category_counts[category] = self.category_counts.get(category, 0) + 1
        
        status_symbol = "[PASS]" if status == "PASS" else "[FAIL]" if status == "FAIL" else "[WARN]"
        try:
            print(f"{status_symbol} [#{res['id']}] [{category}] {name} ({round(duration, 2)}s) -> {status}", flush=True)
        except Exception:
            clean_str = f"{status_symbol} [#{res['id']}] [{category}] {name} ({round(duration, 2)}s) -> {status}".encode('ascii', errors='replace').decode('ascii')
            print(clean_str, flush=True)

    def summary(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        warned = sum(1 for r in self.results if r["status"] == "WARN")
        blocked = sum(1 for r in self.results if r["status"] == "BLOCKED")
        total_time = round(time.time() - self.start_time, 2)
        
        categories_breakdown = {}
        for r in self.results:
            cat = r["category"]
            if cat not in categories_breakdown:
                categories_breakdown[cat] = {"total": 0, "passed": 0, "failed": 0, "warned": 0, "blocked": 0}
            categories_breakdown[cat]["total"] += 1
            status_key = "passed" if r["status"] == "PASS" else "failed" if r["status"] == "FAIL" else "warned" if r["status"] == "WARN" else "blocked"
            categories_breakdown[cat][status_key] += 1

        return {
            "total_test_cases": total,
            "passed": passed,
            "failed": failed,
            "warned": warned,
            "blocked": blocked,
            "pass_rate": f"{(passed / total * 100):.1f}%" if total > 0 else "0%",
            "total_time_seconds": total_time,
            "categories": categories_breakdown,
            "results": self.results
        }

def create_driver(window_size=(1600, 1000)):
    options = ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f"--window-size={window_size[0]},{window_size[1]}")
    options.add_argument("--log-level=3")
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(3)
    return driver

def capture_screen(driver, name):
    try:
        clean_name = "".join(c for c in name if c.isalnum() or c in ('_', '-'))
        filename = f"{clean_name}_{int(time.time()*1000)}.png"
        path = os.path.join(SCREENSHOT_DIR, filename)
        driver.save_screenshot(path)
        return path
    except Exception as e:
        print(f"[!] Screenshot failed: {e}")
        return ""

def login_as(driver, email, password):
    try:
        driver.get(f"{BASE_URL}/auth/login.html")
        driver.execute_script("localStorage.clear(); sessionStorage.clear();")
        driver.get(f"{BASE_URL}/auth/login.html")
        time.sleep(1.0)
        
        user_inp = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#username, input[type='text'], input[type='email']"))
        )
        pass_inp = driver.find_element(By.CSS_SELECTOR, "#password, input[type='password']")
        btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], #loginBtn, .btn-primary")
        
        user_inp.clear()
        user_inp.send_keys(email)
        pass_inp.clear()
        pass_inp.send_keys(password)
        try:
            btn.click()
        except Exception:
            driver.execute_script("document.getElementById('loginForm').dispatchEvent(new Event('submit', {cancelable: true, bubbles: true}));")
        
        try:
            WebDriverWait(driver, 10).until(
                lambda d: ("login" not in d.current_url.lower() and ("admin" in d.current_url.lower() or "dashboard" in d.current_url.lower() or "project" in d.current_url.lower()))
            )
        except Exception:
            time.sleep(2)
        return True
    except Exception as e:
        print(f"[!] Login error for {email}: {e}")
        return False

def logout(driver):
    try:
        driver.execute_script("localStorage.clear(); sessionStorage.clear();")
        driver.get(f"{BASE_URL}/auth/login.html")
        time.sleep(0.5)
    except Exception:
        pass
