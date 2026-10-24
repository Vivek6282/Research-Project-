"""
Trackside E2E — Set-up helpers used by conftest.py (kept here so conftest stays short).
"""

from e2e.timeouts import API_TIMEOUT_S

# A valid zone position: zones now need a gps_range (see Prompt 12, P1)
SAMPLE_GPS_RANGE = {"start": {"lat": 12.9716, "lng": 77.5946}, "end": {"lat": 12.9720, "lng": 77.5950}}


def list_results(response):
    """The rows of a list response, whether or not it is paginated."""
    data = response.json()
    return data if isinstance(data, list) else data.get("results", [])


def ensure_track_and_zone(session, backend_url, auth_headers):
    """Make sure one sprint-class track with one corner zone exists; returns the track id."""
    tracks_res = session.get(f"{backend_url}/api/tracks/", timeout=API_TIMEOUT_S)
    assert tracks_res.status_code == 200, f"Failed to fetch tracks: {tracks_res.text}"
    tracks = list_results(tracks_res)
    if not tracks:
        created = session.post(
            f"{backend_url}/api/tracks/", json={"name": "Apex International Circuit", "kart_class": "sprint"},
            headers=auth_headers(), timeout=API_TIMEOUT_S,
        )
        assert created.status_code in (200, 201), f"Failed to create track: {created.status_code} - {created.text}"
        track_id = created.json()["id"]
    else:
        track_id = tracks[0]["id"]

    zones_res = session.get(f"{backend_url}/api/tracks/{track_id}/zones/", timeout=API_TIMEOUT_S)
    assert zones_res.status_code == 200, f"Failed to fetch zones: {zones_res.text}"
    if not list_results(zones_res):
        created_zone = session.post(
            f"{backend_url}/api/tracks/{track_id}/zones/",
            json={"label": "Turn 4 Hairpin", "corner_type": "hairpin", "threshold_g": 1.15, "gps_range": SAMPLE_GPS_RANGE},
            headers=auth_headers(), timeout=API_TIMEOUT_S,
        )
        assert created_zone.status_code in (200, 201), f"Failed to create zone: {created_zone.status_code} - {created_zone.text}"
    return track_id
