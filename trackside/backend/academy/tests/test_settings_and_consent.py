"""
Trackside — Tests for academy settings, driver consent and the consent check (Phase 2.0, task 3).
"""

import uuid

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from accounts.models import AuditLogEntry
from driving_sessions.models import Session
from tracks.models import Track

User = get_user_model()
SETTINGS_URL = "/api/academy/settings/"


class AcademyBase(APITestCase):
    """An admin, a coach and a driver."""

    def setUp(self):
        """Create one person per role."""
        make = lambda e, r: User.objects.create_user(email=e, name=e, password="Passw0rd!12345", role=r)
        self.admin, self.coach, self.driver = make("ac_admin@t.local", "admin"), make("ac_coach@t.local", "coach"), make("ac_driver@t.local", "driver")

    def consent_url(self, user_id):
        """The consent endpoint of one user."""
        return f"/api/academy/drivers/{user_id}/consent/"


class TestRetentionSetting(AcademyBase):
    """Only the admin reads and changes retention; the range is enforced and logged."""

    def test_default_is_twelve_months_and_admin_can_change_it(self):
        """GET 12, PATCH 6, audit entry written."""
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(SETTINGS_URL).json()["retention_months"], 12)
        response = self.client.patch(SETTINGS_URL, {"retention_months": 6}, format="json")
        self.assertEqual((response.status_code, response.json()["retention_months"]), (200, 6))
        self.assertTrue(AuditLogEntry.objects.filter(action="SETTINGS_CHANGED").exists())

    def test_out_of_range_values_are_refused(self):
        """0, 121 and text: 400, nothing changes."""
        self.client.force_authenticate(self.admin)
        for value in (0, 121, "soon"):
            self.assertEqual(self.client.patch(SETTINGS_URL, {"retention_months": value}, format="json").status_code, 400)
        self.assertEqual(self.client.get(SETTINGS_URL).json()["retention_months"], 12)

    def test_coach_and_driver_are_refused(self):
        """Not the admin: 403 for reading and changing."""
        for user in (self.coach, self.driver):
            self.client.force_authenticate(user)
            self.assertEqual(self.client.get(SETTINGS_URL).status_code, 403)
            self.assertEqual(self.client.patch(SETTINGS_URL, {"retention_months": 3}, format="json").status_code, 403)


class TestDriverConsent(AcademyBase):
    """Recording and withdrawing consent and the under-18 flag."""

    def test_admin_records_and_withdraws_consent(self):
        """True stamps a time, false clears it; under-18 is stored; each change is logged."""
        self.client.force_authenticate(self.admin)
        url = self.consent_url(self.driver.id)
        self.assertEqual(self.client.get(url).json()["consent_recorded"], False)
        recorded = self.client.patch(url, {"consent_recorded": True, "is_under_18": True}, format="json").json()
        self.assertEqual((recorded["consent_recorded"], recorded["is_under_18"]), (True, True))
        self.assertIsNotNone(recorded["consent_recorded_at"])
        withdrawn = self.client.patch(url, {"consent_recorded": False}, format="json").json()
        self.assertEqual((withdrawn["consent_recorded"], withdrawn["consent_recorded_at"]), (False, None))
        self.assertEqual(AuditLogEntry.objects.filter(action="CONSENT_CHANGED").count(), 2)

    def test_a_coach_account_and_a_made_up_id_look_the_same(self):
        """Only drivers have consent: a coach's id and a random id both give the same 404."""
        self.client.force_authenticate(self.admin)
        coach = self.client.get(self.consent_url(self.coach.id))
        missing = self.client.get(self.consent_url(uuid.uuid4()))
        self.assertEqual((coach.status_code, coach.json()), (missing.status_code, missing.json()))

    def test_coach_and_driver_cannot_change_consent(self):
        """403 for anyone but the admin, including the driver themself."""
        for user in (self.coach, self.driver):
            self.client.force_authenticate(user)
            response = self.client.patch(self.consent_url(self.driver.id), {"consent_recorded": True}, format="json")
            self.assertEqual(response.status_code, 403)


class TestBiometricsNeedConsent(AcademyBase):
    """Real biometric readings are refused until consent is recorded; demo runs are not affected."""

    def post_biometric(self, session):
        """The driver posts one reading to the session."""
        self.client.force_authenticate(self.driver)
        body = {"recorded_at": timezone.now().isoformat(), "heart_rate": 90, "spo2": 98, "breathing_rate": 15}
        return self.client.post(f"/api/sessions/{session.id}/biometrics/", body, format="json")

    def test_refused_without_consent_and_accepted_with_it(self):
        """403 first; 201 once the admin has recorded consent."""
        track = Track.objects.create(name="Consent Track")
        session = Session.objects.create(driver=self.driver, track=track, started_at=timezone.now())
        self.assertEqual(self.post_biometric(session).status_code, 403)
        User.objects.filter(pk=self.driver.pk).update(consent_recorded_at=timezone.now())
        self.assertEqual(self.post_biometric(session).status_code, 201)

    def test_demo_session_does_not_need_consent(self):
        """Simulated demo data is not personal biometric data."""
        track = Track.objects.create(name="Demo Consent Track")
        session = Session.objects.create(driver=self.driver, track=track, started_at=timezone.now(), is_demo=True)
        self.assertEqual(self.post_biometric(session).status_code, 201)
