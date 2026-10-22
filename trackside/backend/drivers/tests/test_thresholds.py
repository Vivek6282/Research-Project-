"""
Trackside — Unit tests for Driver Zone Threshold validation.

Verifies upper-bound (zone ceiling) and lower-bound (kart-class floor) validation rules.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.test import APITestCase

from tracks.models import Track, Zone
from drivers.models import DriverZoneThreshold

User = get_user_model()


class TestDriverZoneThresholdValidation(APITestCase):

    def setUp(self):
        super().setUp()

        self.coach = User.objects.create_user(
            email="coach_thresh@trackside.local",
            name="Coach Thresh Test",
            role="coach",
            password="Password123!",
        )

        self.driver = User.objects.create_user(
            email="driver_thresh@trackside.local",
            name="Driver Thresh Test",
            role="driver",
            password="Password123!",
        )

        # Sprint-class track (floor: 0.3g)
        self.sprint_track = Track.objects.create(
            name="Sprint GP Circuit",
            kart_class=Track.KartClass.SPRINT,
        )
        self.sprint_zone = Zone.objects.create(
            track=self.sprint_track,
            label="Chicane 1",
            threshold_g=1.40,
        )

        # Rental-class track (floor: 0.3g)
        self.rental_track = Track.objects.create(
            name="Fun Park Track",
            kart_class=Track.KartClass.RENTAL,
        )
        self.rental_zone = Zone.objects.create(
            track=self.rental_track,
            label="Hairpin A",
            threshold_g=0.80,
        )

    def test_clean_rejects_threshold_exceeding_ceiling(self):
        # Exceeds 1.40g ceiling
        threshold = DriverZoneThreshold(
            driver=self.driver,
            zone=self.sprint_zone,
            custom_threshold_g=1.50,
            set_by=self.coach,
        )
        with self.assertRaises(ValidationError) as ctx:
            threshold.clean()
        self.assertIn("cannot exceed", str(ctx.exception))

    def test_clean_rejects_threshold_below_sprint_floor(self):
        # 0.2g is below the floor (0.3g)
        threshold = DriverZoneThreshold(
            driver=self.driver,
            zone=self.sprint_zone,
            custom_threshold_g=0.20,
            set_by=self.coach,
        )
        with self.assertRaises(ValidationError) as ctx:
            threshold.clean()
        self.assertIn("below the plausible floor", str(ctx.exception))
        self.assertIn("sprint-class karts", str(ctx.exception))

    def test_clean_accepts_valid_threshold_within_bounds(self):
        threshold = DriverZoneThreshold(
            driver=self.driver,
            zone=self.sprint_zone,
            custom_threshold_g=1.15,
            set_by=self.coach,
        )
        threshold.clean()  # Should not raise

    def test_api_creating_a_per_driver_limit_is_gone_and_listing_still_works(self):
        """Per-driver limits are retired: POST answers 410 with the map message and stores nothing; GET still lists history."""
        self.client.force_authenticate(user=self.coach)
        payload = {
            "driver": str(self.driver.id),
            "zone": str(self.sprint_zone.id),
            "custom_threshold_g": 0.50,
        }
        response = self.client.post("/api/drivers/thresholds/", payload)
        self.assertEqual(response.status_code, status.HTTP_410_GONE)
        self.assertEqual(
            response.json()["detail"],
            "Limits are set per corner on the map: Maps, then Edit corners. Per-driver limits are no longer used.",
        )
        self.assertEqual(DriverZoneThreshold.objects.count(), 0)
        self.assertEqual(self.client.get("/api/drivers/thresholds/").status_code, status.HTTP_200_OK)
