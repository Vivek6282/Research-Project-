import os
import sys
import re
import base64
import pytest
import requests
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Ensure trackside and e2e are importable
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
for p in [str(parent_dir), str(current_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Set high login rate limit for E2E testing to prevent 429 throttling
os.environ["LOGIN_THROTTLE_RATE"] = "1000/min"

REPORTS_DIR = Path(__file__).parent / "reports"
SCREENSHOTS_DIR = REPORTS_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

# Standard test credentials
ADMIN_CREDENTIALS = {
    "identifier": "admin@trackside.local",
    "username": "TRK-ADMIN-000001",
    "password": "AdminPassword123!",
    "role": "admin",
}

COACH_CREDENTIALS = {
    "identifier": "coach@trackside.local",
    "username": "TRK-COACH-000001",
    "password": "CoachPassword123!",
    "role": "coach",
}

DRIVER1_CREDENTIALS = {
    "identifier": "driver@trackside.local",
    "username": "TRK-DRV-000001",
    "password": "DriverPassword123!",
    "role": "driver",
}

DRIVER2_CREDENTIALS = {
    "identifier": "iyer@trackside.local",
    "username": "TRK-DRV-000002",
    "password": "DriverPassword123!",
    "role": "driver",
}


def pytest_addoption(parser):
    parser.addoption(
        "--headed", action="store_true", default=False, help="Run browser tests in headed mode"
    )
    parser.addoption(
        "--base-url", action="store", default=FRONTEND_URL, help="Base URL of frontend application"
    )


@pytest.fixture(scope="session")
def base_url(request):
    return request.config.getoption("--base-url").rstrip("/")


@pytest.fixture(scope="session")
def backend_url():
    return BACKEND_URL.rstrip("/")


@pytest.fixture(scope="session", autouse=True)
def ensure_test_environment(backend_url):
    """Ensure baseline test accounts exist and are active in the test database."""
    # Attempt to reactivate/seed accounts via API or direct calls
    session = requests.Session()
    try:
        # Check backend health
        resp = session.get(f"{backend_url}/api/auth/csrf/", timeout=5)
        csrf_token = resp.cookies.get("csrftoken", "")

        # Authenticate as admin to verify accounts
        login_res = session.post(
            f"{backend_url}/api/auth/login/",
            json={"identifier": ADMIN_CREDENTIALS["identifier"], "password": ADMIN_CREDENTIALS["password"]},
            headers={"X-CSRFToken": csrf_token, "Referer": backend_url},
            timeout=5,
        )

        if login_res.status_code == 200:
            # Reactivate any deactivated standard accounts
            users_res = session.get(f"{backend_url}/api/auth/users/", timeout=5)
            if users_res.status_code == 200:
                user_list = users_res.json()
                users = user_list if isinstance(user_list, list) else user_list.get("results", [])
                for u in users:
                    if u.get("email") in [ADMIN_CREDENTIALS["identifier"], COACH_CREDENTIALS["identifier"],
                                         DRIVER1_CREDENTIALS["identifier"], DRIVER2_CREDENTIALS["identifier"]]:
                        if not u.get("is_active", True):
                            csrf_token = session.cookies.get("csrftoken", csrf_token)
                            session.patch(
                                f"{backend_url}/api/auth/users/{u['id']}/",
                                json={"is_active": True},
                                headers={"X-CSRFToken": csrf_token, "Referer": backend_url},
                                timeout=5,
                            )

                # Ensure at least one track and session exist for coach / telemetry tests
                tracks_res = session.get(f"{backend_url}/api/tracks/", timeout=5)
                track_id = None
                if tracks_res.status_code == 200:
                    t_data = tracks_res.json()
                    t_list = t_data if isinstance(t_data, list) else t_data.get("results", [])
                    if len(t_list) > 0:
                        track_id = t_list[0]["id"]
                    else:
                        create_track = session.post(
                            f"{backend_url}/api/tracks/",
                            json={"name": "Apex International Circuit", "kart_class": "sprint"},
                            headers={"X-CSRFToken": csrf_token, "Referer": backend_url},
                            timeout=5,
                        )
                        if create_track.status_code in (200, 201):
                            track_id = create_track.json()["id"]

                sess_res = session.get(f"{backend_url}/api/sessions/", timeout=5)
                if sess_res.status_code == 200:
                    s_data = sess_res.json()
                    s_list = s_data if isinstance(s_data, list) else s_data.get("results", [])
                    if len(s_list) == 0 and track_id:
                        driver_user = next((u for u in users if u.get("role") == "driver"), None)
                        if driver_user:
                            import datetime
                            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
                            session.post(
                                f"{backend_url}/api/sessions/",
                                json={
                                    "driver": driver_user["id"],
                                    "track": track_id,
                                    "mode": "safety",
                                    "started_at": now_iso,
                                    "kart_number": "#07",
                                },
                                headers={"X-CSRFToken": csrf_token, "Referer": backend_url},
                                timeout=5,
                            )
    except Exception as e:
        print(f"[conftest] Note during test environment prep: {e}")

    yield


@pytest.fixture
def driver(request, base_url):
    """WebDriver fixture initializing Chrome with headless/headed options."""
    options = Options()
    is_headed = request.config.getoption("--headed")
    if not is_headed:
        options.add_argument("--headless=new")

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1440,900")
    options.add_argument("--log-level=3")

    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1440, 900)
    request.node.driver = driver

    yield driver

    driver.quit()


@pytest.fixture(autouse=True)
def clean_browser_state(driver, base_url):
    """Ensure every test begins with a completely fresh, unauthenticated browser session."""
    driver.get(f"{base_url}/login")
    driver.delete_all_cookies()
    try:
        driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
    except Exception:
        pass
    yield


def get_tc_id(item) -> str:
    """Extract TC-ID from test function docstring or function name."""
    doc = item.function.__doc__ or ""
    match = re.search(r"\b(TC-[A-Z0-9]+-[0-9]+)\b", doc)
    if match:
        return match.group(1)
    
    # Try from function name e.g. test_tc_auth_01 -> TC-AUTH-01
    name_match = re.search(r"test_(tc_[a-z0-9_]+)", item.name, re.IGNORECASE)
    if name_match:
        return name_match.group(1).replace("_", "-").upper()

    return item.name


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    driver = getattr(item, "driver", None)
    if not driver:
        # Check in fixture values
        if hasattr(item, "funcargs") and "driver" in item.funcargs:
            driver = item.funcargs["driver"]

    tc_id = get_tc_id(item)

    if call.when == "call" and driver is not None:
        screenshot_path = SCREENSHOTS_DIR / f"{tc_id}.png"
        try:
            driver.save_screenshot(str(screenshot_path))
            
            # Embed in pytest-html report
            with open(screenshot_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
            
            try:
                import pytest_html
                extra = getattr(report, "extra", [])
                extra.append(pytest_html.extras.image(f"data:image/png;base64,{encoded_string}", name=f"{tc_id} Evidence"))
                report.extra = extra
            except Exception:
                try:
                    from pytest_html import extras
                    if hasattr(report, "extras"):
                        report.extras.append(extras.image(f"data:image/png;base64,{encoded_string}", name=f"{tc_id} Evidence"))
                except Exception:
                    pass
        except Exception as e:
            print(f"[conftest] Could not save screenshot for {tc_id}: {e}")
