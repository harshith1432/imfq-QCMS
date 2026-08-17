"""
QCMS Enterprise OS - Master Selenium Test Runner
Executes comprehensive end-to-end checks on all modules and generates an audit report.
"""

import sys
import os
import json
import time

# Add tests_selenium directory to sys.path
sys.path.insert(0, os.path.dirname(__file__))

from test_base import create_driver, TestReport
from test_suite_auth_and_landing import run_auth_and_landing_tests
from test_suite_super_admin import run_super_admin_tests
from test_suite_dashboards import run_dashboard_tests
from test_suite_8_stage_workflow import run_8_stage_workflow_tests
from test_suite_analytics_and_admin import run_analytics_and_rewards_tests, run_i18n_and_pdf_tests

def main():
    print("=" * 70)
    print("      QCMS ENTERPRISE OS - COMPREHENSIVE SELENIUM SYSTEM AUDIT       ")
    print("=" * 70)
    
    report = TestReport()
    driver = None
    
    try:
        print("\n[+] Initializing Headless Chrome WebDriver...")
        driver = create_driver()
        print("[+] Headless Chrome WebDriver successfully initialized.")

        # Execute test suites
        run_auth_and_landing_tests(driver, report)
        run_super_admin_tests(driver, report)
        run_dashboard_tests(driver, report)
        run_8_stage_workflow_tests(driver, report)
        run_analytics_and_rewards_tests(driver, report)
        run_i18n_and_pdf_tests(driver, report)

    except Exception as e:
        print(f"\n[!] Unexpected error during test execution: {e}")
    finally:
        if driver:
            try:
                driver.quit()
                print("\n[+] Selenium WebDriver closed.")
            except Exception:
                pass

    # Generate Summary
    summary = report.summary()
    print("\n" + "=" * 70)
    print("                        AUDIT SUMMARY RESULTS                         ")
    print("=" * 70)
    print(f"Total Tests Executed: {summary['total']}")
    print(f"Passed:              {summary['passed']}")
    print(f"Failed:              {summary['failed']}")
    print(f"Warnings/Skips:      {summary['warned'] + summary['skipped']}")
    print(f"Pass Rate:           {summary['pass_rate']}")
    print(f"Total Duration:      {summary['total_time_seconds']}s")
    print("=" * 70)

    # Save detailed JSON report
    report_path = os.path.join(os.path.dirname(__file__), "audit_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"[+] Detailed test report saved to: {report_path}")

    return 0 if summary['failed'] == 0 else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
