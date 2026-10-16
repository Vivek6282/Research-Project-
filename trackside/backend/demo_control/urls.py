"""
Trackside — Demo Control URL Configuration.

Routes:
- POST /api/demo/simulator/start/
- POST /api/demo/simulator/stop/
- GET  /api/demo/simulator/status/
"""

from django.urls import path
from demo_control.views import (
    SimulatorStartView,
    SimulatorStopView,
    SimulatorStatusView,
)

urlpatterns = [
    path("simulator/start/", SimulatorStartView.as_view(), name="demo-simulator-start"),
    path("simulator/stop/", SimulatorStopView.as_view(), name="demo-simulator-stop"),
    path("simulator/status/", SimulatorStatusView.as_view(), name="demo-simulator-status"),
]
