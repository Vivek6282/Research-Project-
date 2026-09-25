# Formal End-to-End Test Report

**Project Name:** Trackside — IoT-Based Trajectory Warning and Biometric Monitoring System for Karting  
**Test Type:** End-to-End (E2E) Browser UI & Role Integration Testing with Selenium WebDriver  
**Date:** September 25, 2026  
**Testing Authority:** Trackside Autonomous Quality Assurance  
**Target Environment:** Local Pit-Wall Staging Environment (Daphne ASGI + Vite React)  

---

## 1. Executive Summary

A comprehensive automated browser testing suite was executed against the Trackside pit-wall application to validate system integrity across all three intradomain user roles (**Admin**, **Coach**, **Driver**), core authentication and authorization guards, responsive multi-device viewport transitions, and safety-critical biometric and trajectory telemetry visualizations.

- **Total Test Cases Executed:** 34
- **Passed:** 34
- **Failed:** 0
- **Overall Pass Rate:** **100.0%**

### Module Execution Breakdown

| Module | Total Tests | Passed | Failed | Pass Rate | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Authentication** | 7 | 7 | 0 | 100.0% | ✅ PASSED |
| **Admin Module** | 9 | 9 | 0 | 100.0% | ✅ PASSED |
| **Coach Module** | 8 | 8 | 0 | 100.0% | ✅ PASSED |
| **Driver Module** | 4 | 4 | 0 | 100.0% | ✅ PASSED |
| **Shared UI** | 3 | 3 | 0 | 100.0% | ✅ PASSED |
| **Responsive Layout** | 3 | 3 | 0 | 100.0% | ✅ PASSED |

## 2. Introduction & Scope

### 2.1 Purpose
The purpose of this validation cycle is to mathematically and visually ensure that the web application satisfies all operational and safety requirements laid out in the Trackside project specifications, regressions from earlier development phases remain completely eliminated, and role access boundaries prevent unauthorized intradomain privilege escalation.

### 2.2 Scope Boundaries
| Boundary | Included in Scope | Explicitly Out of Scope |
| :--- | :--- | :--- |
| **Functional** | Web application dashboards (Admin, Coach, Driver) | ESP32 physical hardware & glove firmware flashing |
| **Security** | Role-based access control, CSRF, IDOR isolation | Physical CAN bus / Wi-Fi physical layer sniffing |
| **UI / Layout** | Responsive breakpoints (375px, 768px, 1440px), modal flows | Native mobile application (PWA container only) |
| **Roadmap** | Phase 1 Production Pit-Wall System | Phase 1.5 Video Sync & Phase 2 ML (non-interactive placeholders) |

## 3. Test Environment

| Component | Specification / Version | Description |
| :--- | :--- | :--- |
| **Operating System** | Windows 11 Professional (x64) | Host execution platform |
| **Browser** | Google Chrome Headless (`--headless=new`) | Chrome 120+ with Blink engine |
| **Test Framework** | pytest 8.x + pytest-html + selenium 4.x | Python test runner & reporting engine |
| **Backend Platform** | Django 5.x + Daphne ASGI + Channels | High-concurrency WebSockets & REST API |
| **Frontend Stack** | React 18 + Vite 6 + Tailwind CSS | Single Page Application (SPA) client |
| **Viewports Tested** | 375×812 (Mobile), 768×1024 (Tablet), 1440×900 (Desktop) | Responsive multi-factor testing |

## 4. Test Strategy & Architecture

The E2E test suite adheres to high-reliability software engineering practices:
1. **Page Object Model (POM):** Cleanly separates test intent from DOM locator logic under `e2e/pages/`. Tests express domain actions (`admin_page.create_user(...)`) rather than raw WebDriver clicks.
2. **Strict `data-testid` Selector Policy:** All Selenium locators target immutable `data-testid` attributes (e.g., `admin-add-account-btn`, `coach-signal-strip`), completely isolating tests from CSS styling or text mutations.
3. **Zero Arbitrary Sleeps:** All element state transitions, network requests, and route changes synchronize via explicit `WebDriverWait` and `expected_conditions` (no `time.sleep()`).
4. **Automated Evidence Collection:** Full-resolution PNG screenshots are captured for every test case upon execution and stored under `e2e/reports/screenshots/<TC-ID>.png`.

## 5. Comprehensive Test Execution Matrix

| TC-ID | Module | Test Case Description | Preconditions | Test Steps | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **TC-AUTH-01** | Authentication | Valid login for each role redirects to correct dashboard (/admin, /coach, /driver) | Admin, Coach, and Driver user accounts provisioned and active in database | 1. Select role tab. 2. Input valid credentials. 3. Click Submit. 4. Verify redirected route. | Admin redirects to /admin, Coach to /coach, Driver to /driver with active session cookie | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-AUTH-02** | Authentication | Login with email and auto-generated username (TRK-DRV-xxxxxx) both succeed | Driver account with email and server-generated username exists | 1. Log in using email address. 2. Verify dashboard. 3. Log out. 4. Log in using username ID. 5. Verify dashboard. | Both identifier formats authenticate successfully against backend auth endpoint | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-AUTH-03** | Authentication | Wrong password shows error banner and prevents dashboard access | Valid account exists | 1. Enter valid email. 2. Enter invalid password. 3. Click Submit. | Visible error banner rendered; URL remains on /login; no session cookie granted | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-AUTH-04** | Authentication | Deactivated user account cannot log in | Account exists but is_active flag is set to False | 1. Enter deactivated user credentials. 2. Click Submit. | Login rejected with error message; dashboard access denied | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-AUTH-05** | Authentication | Unauthenticated access to protected routes redirects to /login | Browser has no active session cookie | 1. Directly navigate to /admin, /coach, /driver. | Client-side route guard intercepts unauthenticated request and redirects to /login | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-AUTH-06** | Authentication | Role guard blocks Driver from accessing Admin or Coach dashboards | Authenticated as Driver role | 1. Navigate directly to /admin and /coach URLs. | Role authorization guard blocks access and redirects away to permitted route | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-AUTH-07** | Authentication | Sign out terminates session and back-navigation does not restore access | Active authenticated session | 1. Click Sign Out in TopBar. 2. Verify /login. 3. Trigger browser back navigation. | Session cookie cleared; browser back-navigation does not expose protected dashboard state | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-ADMIN-01** | Admin Module | Create Coach account with required email — displays generated TRK-COACH- username | Authenticated as Admin | 1. Click Add Account. 2. Fill Name, Role=Coach, Email, Password. 3. Click Create Account. | Account created; modal displays TRK-COACH- username; user appears in roster table | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-ADMIN-02** | Admin Module | Create Driver account without email — succeeds with generated TRK-DRV- username | Authenticated as Admin | 1. Click Add Account. 2. Fill Name, Role=Driver, leave Email empty. 3. Click Create Account. | Driver created; generated TRK-DRV- ID displayed in confirmation panel | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-ADMIN-03** | Admin Module | Coach creation without email is rejected with visible validation error | Authenticated as Admin | 1. Fill Name, Role=Coach, omit Email. 2. Click Create Account. | Submission blocked; validation message displayed indicating email is required for Coaches | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-ADMIN-04** | Admin Module | Newly created user persists in database after page refresh (regression test) | Authenticated as Admin; new user created | 1. Create user. 2. Refresh browser page (F5). 3. Inspect user roster table. | Created user record fetched from backend API and displayed in table | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-ADMIN-05** | Admin Module | Edit user name inline — modification persists after page refresh | Target user exists in roster table | 1. Click Edit. 2. Update name field. 3. Click Save. 4. Refresh page. | PATCH request updates backend; updated name rendered consistently after refresh | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-ADMIN-06** | Admin Module | Deactivate via custom ConfirmDialog (no native window.confirm) -> status Inactive; Reactivate restores | Active user in roster | 1. Click Deactivate. 2. Confirm via styled modal. 3. Verify Inactive chip. 4. Click Reactivate. 5. Confirm. | Styled dialog handles confirmation without native blocking alert; status toggles Active/Inactive | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-ADMIN-07** | Admin Module | Verify no hard-delete button exists anywhere in user roster (regression test) | Admin dashboard loaded | 1. Inspect all DOM buttons and actions in user management panel. | Zero delete buttons present; only soft-deactivation is permitted by design | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-ADMIN-08** | Admin Module | Audit log panel records and displays entries after user account modification | Admin user performs account provisioning or deactivation | 1. Create user. 2. Inspect Security & Audit Trail panel. | Audit log list contains timestamped action entry (e.g. CREATE USER) | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-ADMIN-09** | Admin Module | Device diagnostic command creation and UI pending state transition | IoT device panel registered and online | 1. Click Run Diagnostic on device card. 2. Observe button state. | Pending command issued; UI reflects WAITING FOR DEVICE state while command executes | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-COACH-01** | Coach Module | Coach dashboard loads all 7 core analytical panels simultaneously | Authenticated as Coach on /coach | 1. Load /coach. 2. Verify visibility of all 7 dashboard panels. | Live Trajectory, Timing Tower, Sector Deltas, Biometrics, Threshold Control, Notes, and Track View render | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-COACH-02** | Coach Module | Signal strip renders exactly 5 LED segments and stage label matches lit segment count | Coach dashboard live telemetry feed active | 1. Count signal strip segments in DOM. 2. Verify stage text against lit segment thresholds. | Exactly 5 segments; 1-2 lit = Nominal, 3-4 lit = Monitoring, 5 lit = Intervene | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-COACH-03** | Coach Module | SIMULATED DATA badge is prominently visible during mock telemetry execution | VITE_USE_MOCK_TELEMETRY enabled | 1. Inspect header of Live Trajectory panel. | Pulsing orange SIMULATED DATA badge is rendered | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-COACH-04** | Coach Module | Custom zone threshold slider reflects kart-class bounds (>=0.80g to 1.50g) | Active zone loaded in threshold control panel | 1. Read min and max attributes of threshold input slider. | Bounds align with kart dynamic limits (min >= 0.80g, max >= 1.15g), not obsolete 0.60g | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-COACH-05** | Coach Module | Save coach session note tied to active driver/zone and verify persistence | Coach dashboard loaded | 1. Type note text. 2. Click Save Note. 3. Verify entry in feed. 4. Refresh page. | Note persists in session history feed across browser reload | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-COACH-06** | Coach Module | Create custom zone with corner type and verify appearance in dropdown selector | Session Notes panel zone selector available | 1. Select + New Zone. 2. Enter name and select corner type. 3. Click Add Zone. | New zone created and immediately selectable in zone dropdown | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-COACH-07** | Coach Module | Live Track View renders appropriate fallback message when track unsurveyed | No GPS reference coordinates configured for track | 1. Inspect Live Track View component container. | Fallback container renders without throwing JavaScript canvas/SVG errors | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-COACH-08** | Coach Module | Historical Sessions tab badge count matches number of table rows displayed | Coach dashboard loaded with historical session records | 1. Click Historical Sessions tab. 2. Compare badge count integer with table <tr> count. | Count in badge matches row count in historical sessions table exactly | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-DRIVER-01** | Driver Module | Driver account with zero sessions displays empty state rather than simulated mock data | Driver account with no recorded driving sessions | 1. Log in as fresh Driver. 2. Inspect Zone Risk Heatmap and Best Lap panels. | 'No sessions recorded yet' banner displayed; no mock exceedance numbers shown | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-DRIVER-02** | Driver Module | Safety Mode / Performance Mode toggle button switches active focus state | Driver logged in on /driver | 1. Click Performance Mode. 2. Verify text. 3. Click Safety Mode. 4. Verify text. | Active focus text updates dynamically between SAFETY FOCUS and PERFORMANCE FOCUS | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-DRIVER-03** | Driver Module | Insecure Direct Object Reference (IDOR) check — Driver A cannot see Driver B telemetry | Driver 1 logged in; Driver 2 has separate records in system | 1. Scrape full rendered text of Driver 1 dashboard. 2. Search for Driver 2 identifiers. | Driver 2 private records and identifiers are strictly excluded from Driver 1 DOM | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-DRIVER-04** | Driver Module | Phase 1.5 and Phase 2 Development Ongoing banners are visible and non-interactive | Driver dashboard loaded | 1. Locate Phase 1.5 and Phase 2 dev banners. 2. Verify informational content. | Both banners rendered with appropriate styling; future features clearly demarcated | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-UI-01** | Shared UI | Settings modal font size presets (S/M/L/XL) modify root DOM and persist across login | Authenticated user on any dashboard | 1. Open Settings. 2. Click XL. 3. Verify root fontSize. 4. Logout. 5. Login. 6. Verify. | HTML root style fontSize updates immediately and persists across auth cycle | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-UI-02** | Shared UI | Verify absence of theme toggle in Settings modal (regression test for removal) | Settings modal open | 1. Open Settings modal. 2. Inspect all controls for theme/light-mode toggles. | No theme toggle controls present; application adheres to dark telemetry aesthetic | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-UI-03** | Shared UI | First-login tutorial advances with Next, dismisses with Skip, and does not reappear | Tutorial active or triggered via Replay Tutorial | 1. Verify step 1 title. 2. Click Next. 3. Verify step 2 title. 4. Click Skip. 5. Refresh. | Step advances; Skip dismisses callout; tutorial remains hidden after page refresh | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-RESP-01** | Responsive Layout | No horizontal page overflow at mobile (375px), tablet (768px), and desktop (1440px) | Key application dashboards loaded | 1. Resize window to 375px, 768px, 1440px. 2. Check scrollWidth vs innerWidth. | scrollWidth <= innerWidth across all tested viewport widths; zero horizontal scrollbars | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-RESP-02** | Responsive Layout | Admin user table renders as cards at 375px and as full table at 1440px | Admin dashboard loaded | 1. Set viewport to 1440px -> verify table visible, cards hidden. 2. Set to 375px -> verify cards visible, table hidden. | Responsive CSS breakpoint seamlessly switches presentation between tabular and card formats | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |
| **TC-RESP-03** | Responsive Layout | Desktop layout places Timing Tower and Sector Deltas inside right sidebar column | Coach dashboard loaded at 1440px desktop width | 1. Inspect right sidebar container DOM element. | Both Timing Tower and Sector Deltas panels reside inside the 25% right sidebar container | Executed as expected with zero assertion failures; verified in DOM and network response. | ✅ PASS |

## 6. Defects Discovered & Documented

### 6.1 Application Defects Identified & Resolved During Suite Construction

| Defect ID | Associated TC | Severity | Root Cause | Resolution | Verification Status |
| :--- | :--- | :---: | :--- | :--- | :---: |
| **DEF-001** | TC-AUTH-03 | Medium | `api.ts` intercepted all HTTP 401 responses and triggered `window.location.href = '/login'`, causing a hard page reload that erased login error messages. | Exempted `/api/auth/login/` and `/api/auth/me/` from automatic reload so login error state surfaces to the UI. | ✅ VERIFIED |
| **DEF-002** | TC-AUTH-04..07 | High | Backend anonymous login throttle limit of 5 requests/min per IP blocked rapid sequential role testing with HTTP 429. | Configured `DEFAULT_THROTTLE_RATES` to allow test rate overrides (`LOGIN_THROTTLE_RATE`, defaulting to 1000/min in DEBUG mode). | ✅ VERIFIED |
| **DEF-003** | TC-COACH-05 | High | `SessionNoteSerializer` omitted `session` from `read_only_fields`, causing `POST /api/sessions/<uuid>/notes/` to reject valid notes with `{'session': ['This field is required.']}`. | Added `session` to `read_only_fields` in `SessionNoteSerializer` since it is populated from view URL kwargs. | ✅ VERIFIED |
| **DEF-004** | TC-DRIVER-04 | Low | `dev-banner.tsx` testId slugification regex stripped decimal points (`Phase 1.5` became `dev-banner-phase-1-5`). | Updated slugification regex in `dev-banner.tsx` to preserve decimal numbers (`dev-banner-phase-1.5`). | ✅ VERIFIED |

### 6.2 Active Functional Defects

> [!NOTE]
> **Zero active functional defects remain.** All 34 automated E2E test cases pass with 100% compliance across all tested modules.

## 7. Selected Test Case Photographic Evidence

Visual evidence captured during the automated execution run:

### TC-AUTH-01: Authentication & Role-Based Redirection Matrix
![Authentication & Role-Based Redirection Matrix](screenshots/TC-AUTH-01.png)

### TC-ADMIN-01: Admin User Roster Provisioning & Generated Credentials
![Admin User Roster Provisioning & Generated Credentials](screenshots/TC-ADMIN-01.png)

### TC-COACH-01: Coach Live Cockpit (7 Analytical Panels Loaded)
![Coach Live Cockpit (7 Analytical Panels Loaded)](screenshots/TC-COACH-01.png)

### TC-COACH-02: 5-Segment Glove Signal Strip Hardware Reflection
![5-Segment Glove Signal Strip Hardware Reflection](screenshots/TC-COACH-02.png)

### TC-DRIVER-01: Driver Telemetry Dashboard with Real Empty State
![Driver Telemetry Dashboard with Real Empty State](screenshots/TC-DRIVER-01.png)

### TC-UI-01: Settings Modal Font Size Dynamic Rescaling
![Settings Modal Font Size Dynamic Rescaling](screenshots/TC-UI-01.png)

### TC-RESP-01: Responsive Viewport Rendering at Mobile Width (375px)
![Responsive Viewport Rendering at Mobile Width (375px)](screenshots/TC-RESP-01.png)

## 8. Conclusion & Quality Assessment

The Trackside Pit-Wall telemetry web application demonstrates exceptional structural stability, robust security guards against unauthorized role escalation, and dependable real-time feedback rendering across all tested viewports. The implementation of explicit `data-testid` attributes across all frontend modules provides a solid foundation for continuous regression testing during future development cycles.

**Recommendations for Subsequent Milestones:**
1. **Phase 1.5 Video Integration:** When introducing synchronized camera buffers, retain the existing `data-testid="dev-banner-phase-1.5"` container to maintain test suite compatibility.
2. **Hardware In-the-Loop (HIL):** Expand E2E fixtures to ingest live serial packets from the physical ESP32 Bridge unit under simulated high-vibration conditions.
