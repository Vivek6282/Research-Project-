"""
Trackside — Synthetic kart track for import tests (NOT a real recording).

Builds a closed lap shaped like a rounded rectangle with four corners of known
radius, so tests can check the outline and corner finder against known answers.
It can also write RaceChrono CSV v3 and Racelogic VBO text from the same data.
"""

import math
import random

ORIGIN_LAT, ORIGIN_LNG = 12.9716, 77.5946
METERS_PER_DEG_LAT = 111_194.9
# Corner radii in driving order (counter-clockwise, starting on the bottom straight)
CORNER_RADII = [20.0, 12.0, 30.0, 25.0]
WIDTH, HEIGHT = 220.0, 100.0


def lap_segments():
    """List the lap as ('line', length) and ('arc', radius) pieces, all left turns."""
    r_br, r_tr, r_tl, r_bl = CORNER_RADII
    return [
        ("line", WIDTH - r_bl - r_br), ("arc", r_br),
        ("line", HEIGHT - r_br - r_tr), ("arc", r_tr),
        ("line", WIDTH - r_tr - r_tl), ("arc", r_tl),
        ("line", HEIGHT - r_tl - r_bl), ("arc", r_bl),
    ]


def lap_length():
    """Total length of one lap in metres."""
    return sum(v if kind == "line" else v * math.pi / 2 for kind, v in lap_segments())


def position_at(distance):
    """Return (x, y) in metres at the given distance along the lap (wraps every lap)."""
    distance %= lap_length()
    x, y, heading = CORNER_RADII[3], 0.0, 0.0
    for kind, value in lap_segments():
        length = value if kind == "line" else value * math.pi / 2
        if distance <= length:
            if kind == "line":
                return x + distance * math.cos(heading), y + distance * math.sin(heading)
            cx, cy = x - value * math.sin(heading), y + value * math.cos(heading)
            phi = heading - math.pi / 2 + distance / value
            return cx + value * math.cos(phi), cy + value * math.sin(phi)
        distance -= length
        if kind == "line":
            x, y = x + length * math.cos(heading), y + length * math.sin(heading)
        else:
            cx, cy = x - value * math.sin(heading), y + value * math.cos(heading)
            heading += math.pi / 2
            phi = heading - math.pi / 2
            x, y = cx + value * math.cos(phi), cy + value * math.sin(phi)
    return CORNER_RADII[3], 0.0


def to_lat_lng(x, y):
    """Convert local metres to latitude/longitude around the origin."""
    lat = ORIGIN_LAT + y / METERS_PER_DEG_LAT
    lng = ORIGIN_LNG + x / (METERS_PER_DEG_LAT * math.cos(math.radians(ORIGIN_LAT)))
    return lat, lng


def make_samples(laps=3, step=2.2, noise=0.25, seed=42):
    """Return [(lat, lng, lap_number)] for several laps with small GPS noise."""
    rng = random.Random(seed)
    per_lap = int(lap_length() // step) + 1
    samples = []
    for lap in range(1, laps + 1):
        for i in range(per_lap):
            x, y = position_at(i * step)
            lat, lng = to_lat_lng(x + rng.gauss(0, noise), y + rng.gauss(0, noise))
            samples.append((lat, lng, lap))
    return samples


def racechrono_csv_text(samples, with_lap=True, bad_rows=True):
    """Write the samples as a SYNTHETIC RaceChrono CSV v3 file (text)."""
    lines = [
        "This file is SYNTHETIC test data, not a real RaceChrono recording",
        "Format,3", 'Session title,"Synthetic test session"', "Session type,Lap timing",
        'Track name,"Synthetic Test Track"', "", "",
    ]
    lap_head = ",lap_number" if with_lap else ""
    lines.append(f"timestamp,latitude,longitude,speed,latitude,longitude{lap_head}")
    lines.append(f"s,deg,deg,m/s,deg,deg{',' if with_lap else ''}")
    lines.append(f"gps,gps,gps,gps,calculated,calculated{',' if with_lap else ''}")
    if bad_rows:
        lines.append(f"0.0,,,0.0,,{',1' if with_lap else ''}")
        lines.append(f"0.1,nan,77.5,0.0,nan,77.5{',1' if with_lap else ''}")
        lines.append(f"0.2,95.0,77.5,0.0,95.0,77.5{',1' if with_lap else ''}")
    for index, (lat, lng, lap) in enumerate(samples):
        lap_cell = f",{lap}" if with_lap else ""
        lines.append(f"{index * 0.1:.1f},{lat:.8f},{lng:.8f},22.0,{lat + 0.001:.8f},{lng + 0.001:.8f}{lap_cell}")
    return "\n".join(lines) + "\n"


def vbo_text(samples):
    """Write the samples as a SYNTHETIC Racelogic VBO file (minutes, longitude positive = West)."""
    lines = ["File created on SYNTHETIC test data, not a real recording", "", "[header]", "satellites", "time",
             "latitude", "longitude", "velocity kmh", "", "[column names]", "sats time lat long velocity", "", "[data]"]
    for index, (lat, lng, _lap) in enumerate(samples):
        lines.append(f"010 {120000 + index * 0.1:.2f} {lat * 60:+.5f} {-lng * 60:+.5f} 79.2")
    return "\n".join(lines) + "\n"
