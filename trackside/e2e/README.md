# Trackside — End-to-End (E2E) Selenium Test Suite

Comprehensive automated browser test suite for the **Trackside** IoT-Based Trajectory Warning and Biometric Monitoring System for Karting, built with Selenium WebDriver and pytest.

## Architecture

- **Page Object Model (POM):** Cleanly organized under `e2e/pages/` (`LoginPage`, `AdminDashboardPage`, `CoachDashboardPage`, `DriverDashboardPage`, `SettingsModal`, `TutorialCallout`).
- **Selector Policy:** 100% strict `data-testid` locator strategy — tests are completely insulated against CSS and layout refactoring.
- **Synchronization:** Exclusively explicit `WebDriverWait` and `expected_conditions` — zero arbitrary `time.sleep()`.
- **Evidence Collection:** Automatically captures screenshots upon test execution to `e2e/reports/screenshots/<TC-ID>.png`.

## Test Execution

### Single Command Execution

To run the complete test suite, generate the self-contained HTML report with embedded screenshot evidence, and produce the formal academic Markdown report, execute the following commands from the `trackside/` directory:

```bash
pytest e2e/ --html=e2e/reports/e2e_report.html --self-contained-html --json-report --json-report-file=e2e/reports/report.json
python e2e/generate_report.py
```

### Options

- **Headed Mode (Visual Execution):**
  ```bash
  pytest e2e/ --headed
  ```
- **Run Specific Module:**
  ```bash
  pytest e2e/test_auth.py
  pytest e2e/test_admin.py
  pytest e2e/test_coach.py
  pytest e2e/test_driver.py
  pytest e2e/test_shared_ui.py
  pytest e2e/test_responsive.py
  ```

## Reports Generated

1. `e2e/reports/e2e_report.html`: Self-contained interactive HTML test report with embedded visual evidence screenshots.
2. `e2e/reports/SELENIUM_TEST_REPORT.md`: Submission-ready, formal academic markdown report containing methodology, complete test execution matrix, defect documentation, and environment specifications.
3. `e2e/reports/screenshots/`: Individual PNG evidence screenshots organized by Test Case ID (`TC-ID.png`).
