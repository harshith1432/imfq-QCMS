"""
Selenium Master Test Suite for QCMS Enterprise OS
Checks every single module, route, and feature of the platform.
"""

import os
import sys
import time
import json
import traceback
from datetime import datetime
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

class TestReport:
    def __init__(self):
        self.results = []
        self.start_time = time.time()

    def record(self, category, name, status, details="", duration=0.0):
        self.results.append({
            "category": category,
            "name": name,
            "status": status,  # PASS, FAIL, SKIP, WARN
            "details": details,
            "duration": round(duration, 3),
            "timestamp": datetime.now().isoformat()
        })
        status_symbol = "[PASS]" if status == "PASS" else "[FAIL]" if status == "FAIL" else "[WARN]"
        print(f"{status_symbol} [{category}] {name} ({round(duration, 2)}s) - {details[:100]}")

    def summary(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        warned = sum(1 for r in self.results if r["status"] == "WARN")
        skipped = sum(1 for r in self.results if r["status"] == "SKIP")
        total_time = round(time.time() - self.start_time, 2)
        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "warned": warned,
            "skipped": skipped,
            "pass_rate": f"{(passed / total * 100):.1f}%" if total > 0 else "0%",
            "total_time_seconds": total_time,
            "results": self.results
        }

def create_driver():
    options = ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1600,1000")
    options.add_argument("--log-level=3")
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(4)
    return driver

def save_screenshot(driver, name):
    try:
        path = os.path.join(SCREENSHOT_DIR, f"{name}_{int(time.time())}.png")
        driver.save_screenshot(path)
        return path
    except Exception:
        return None
