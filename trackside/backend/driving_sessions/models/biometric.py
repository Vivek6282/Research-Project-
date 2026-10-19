"""
Trackside Driving Sessions — Biometric Reading Model.
This module defines the driver wearable sensor data model capturing heart rate,
blood oxygen saturation (SpO2), and respiration metrics during driving sessions.
"""

import uuid
from django.db import models
from driving_sessions.models.session import Session


class BiometricReading(models.Model):
    """
    A single biometric reading from wearable driver telemetry (heart rate, SpO2, breathing rate).
    Correlated with concurrent kart telemetry to assist coaches with driver fatigue and stress assessment.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="biometric_readings",
        help_text="The session this biometric reading belongs to",
    )

    recorded_at = models.DateTimeField(
        help_text="Timestamp of this biometric reading",
    )

    heart_rate = models.IntegerField(
        help_text="Heart rate in BPM",
    )

    spo2 = models.IntegerField(
        help_text="Blood oxygen saturation percentage (SpO2)",
    )

    breathing_rate = models.IntegerField(
        null=True,
        blank=True,
        help_text="Breathing rate in breaths per minute",
    )

    class Meta:
        app_label = "driving_sessions"
        db_table = "biometric_readings"
        ordering = ["session", "recorded_at"]

    def __str__(self):
        return f"Biometric {self.session_id} @ {self.recorded_at}"
