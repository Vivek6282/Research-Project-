"""
Trackside — Unit tests for Data-Driven Track Survey Zone Detection Algorithm.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from tracks.models import Track

User = get_user_model()


class TestTrackSurveyZoneDetection(APITestCase):

    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_superuser(
            email="admin_survey_test@trackside.local",
            name="Survey Admin",
            password="AdminPassword123!",
        )
        self.client.force_authenticate(user=self.admin)
        self.track = Track.objects.create(name="Survey Test Track")

    def test_less_than_3_points_returns_400_validation_error(self):
        url = f"/api/tracks/{self.track.id}/survey/"

        # Test empty payload
        response = self.client.post(url, [], format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "at least 3 valid GPS points" in response.json()["detail"]

        # Test 2 points payload
        two_pts = [
            {"lat": 11.016842, "lng": 76.955831},
            {"lat": 11.017120, "lng": 76.956110},
        ]
        response = self.client.post(url, two_pts, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "at least 3 valid GPS points" in response.json()["detail"]

    def test_different_corner_shapes_produce_different_candidate_zones(self):
        url = f"/api/tracks/{self.track.id}/survey/"

        # Trace A: Tight 180° hairpin turn trace (sharp heading change)
        hairpin_trace = [
            {"lat": 11.016800, "lng": 76.955800},
            {"lat": 11.017200, "lng": 76.955800},  # Going North
            {"lat": 11.017400, "lng": 76.956000},  # Turn East
            {"lat": 11.017400, "lng": 76.956400},  # Sharp Hairpin Apex
            {"lat": 11.017200, "lng": 76.956600},  # Turn South
            {"lat": 11.016800, "lng": 76.956600},  # Going South
        ]

        # Trace B: Gentle 45° sweeper corner trace at different coordinates
        sweeper_trace = [
            {"lat": 12.050000, "lng": 77.050000},
            {"lat": 12.051000, "lng": 77.050000},  # Going North
            {"lat": 12.052000, "lng": 77.050500},  # Gentle curve East
            {"lat": 12.053000, "lng": 77.051200},  # Sweeper apex
            {"lat": 12.054000, "lng": 77.052000},  # Gentle exit
            {"lat": 12.055000, "lng": 77.053000},  # Straight exit
        ]

        # Submit Hairpin Trace
        res_a = self.client.post(url, hairpin_trace, format="json")
        assert res_a.status_code == status.HTTP_200_OK
        zones_a = res_a.json()["candidate_zones"]

        # Submit Sweeper Trace
        res_b = self.client.post(url, sweeper_trace, format="json")
        assert res_b.status_code == status.HTTP_200_OK
        zones_b = res_b.json()["candidate_zones"]

        # Verify that candidate zone outputs are genuinely data-driven and different
        assert zones_a != zones_b
        assert zones_a[0]["start_lat"] != zones_b[0]["start_lat"]
        assert zones_a[0]["start_lng"] != zones_b[0]["start_lng"]
        # Hairpin corner should have a tighter threshold (1.15) than gentle sweeper (1.20/1.25)
        assert zones_a[0]["max_g_threshold"] < zones_b[0]["max_g_threshold"]

    def test_multi_lap_averaging_reduces_noise(self):
        url = f"/api/tracks/{self.track.id}/survey/"

        lap1 = [
            {"lat": 10.0, "lng": 20.0},
            {"lat": 10.2, "lng": 20.0},
            {"lat": 10.4, "lng": 20.5},
            {"lat": 10.4, "lng": 21.0},
        ]
        lap2 = [
            {"lat": 10.0, "lng": 20.0},
            {"lat": 10.4, "lng": 20.0},
            {"lat": 10.6, "lng": 20.5},
            {"lat": 10.6, "lng": 21.0},
        ]

        payload = {"laps": [lap1, lap2]}
        response = self.client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_200_OK

        self.track.refresh_from_db()
        ref_line = self.track.reference_line
        # Verify point 1 lat was averaged ( (10.2 + 10.4)/2 = 10.3 )
        assert ref_line[1]["lat"] == 10.3

