"""
Trackside — Generate the SYNTHETIC ML demo data set (Phase 2.3).

Made-up corner data for 8 drivers over 12 sessions each, to demonstrate the two
"needs your own data" ML features before real sessions exist:
  - driving-style badges (clustering drivers by how they take corners)
  - lap/corner anomaly flags (a pass that is unusual for that driver)

    py ml_demo_data.py                 # writes ml_demo_data/ next to this file
    py ml_demo_data.py --out some/dir --seed 7

Every file says SYNTHETIC in its name column or header. Never present it as real
driver data. The same seed always gives the same files.
"""

import argparse
import csv
import os
import random
from datetime import date, timedelta
from statistics import mean, pstdev
from typing import Dict, List

from ml_demo_styles import (
    ANOMALY_KINDS, ANOMALY_RATE, CORNERS, DRIVERS, NEUTRAL_BRAKE_POINT_M, NEUTRAL_GRIP_USE, STYLES,
)

SESSIONS_PER_DRIVER = 12
LAPS_PER_SESSION = 10
FIRST_SESSION_DATE = date(2026, 7, 6)
DAYS_BETWEEN_SESSIONS = 7
DEFAULT_SEED = 2026
DEFAULT_OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ml_demo_data")

CORNER_COLUMNS = ["driver_id", "driver_name", "session_number", "session_date", "lap_number", "corner",
                  "corner_limit_g", "brake_point_m", "entry_speed_kmh", "peak_lateral_g", "grip_use",
                  "corner_time_s", "true_style", "true_anomaly", "anomaly_kind"]


def corner_time_s(corner, brake_point_m, grip_use, session_number, style, rng) -> float:
    """Time through the corner: braking earlier and using less grip cost time; practice saves a little."""
    time_s = corner.base_time_s
    time_s *= 1 + 0.004 * (brake_point_m - NEUTRAL_BRAKE_POINT_M)
    time_s *= 1 - 0.30 * (grip_use - NEUTRAL_GRIP_USE)
    time_s *= 1 - style.improvement_per_session * (session_number - 1)
    return time_s * (1 + rng.gauss(0, 0.006))


def one_corner_pass(driver, session_number, session_day, lap, corner, rng) -> dict:
    """One row: how this driver took this corner on this lap, with an anomaly injected now and then."""
    driver_id, driver_name, style_name = driver
    style = STYLES[style_name]
    brake_point = rng.gauss(style.brake_point_mean_m, style.brake_point_spread_m)
    grip_use = rng.gauss(style.grip_use_mean, style.grip_use_spread)
    anomaly_kind = rng.choice(sorted(ANOMALY_KINDS)) if rng.random() < ANOMALY_RATE else ""
    time_factor = 1.0
    if anomaly_kind:
        shift = ANOMALY_KINDS[anomaly_kind]
        brake_point += shift["brake_shift_m"]
        grip_use += shift["grip_shift"]
        time_factor = shift["time_factor"]
    brake_point = max(brake_point, 5.0)
    grip_use = min(max(grip_use, 0.30), 1.40)
    time_s = corner_time_s(corner, brake_point, grip_use, session_number, style, rng) * time_factor
    entry_kmh = corner.base_entry_kmh * (1 + 0.10 * (grip_use - NEUTRAL_GRIP_USE)) * (1 + rng.gauss(0, 0.01))
    return {
        "driver_id": driver_id, "driver_name": driver_name, "session_number": session_number,
        "session_date": session_day.isoformat(), "lap_number": lap, "corner": corner.label,
        "corner_limit_g": corner.limit_g, "brake_point_m": round(brake_point, 1),
        "entry_speed_kmh": round(entry_kmh, 1), "peak_lateral_g": round(grip_use * corner.limit_g, 3),
        "grip_use": round(grip_use, 3), "corner_time_s": round(time_s, 3), "true_style": style_name,
        "true_anomaly": int(bool(anomaly_kind)), "anomaly_kind": anomaly_kind,
    }


def generate_corner_rows(seed: int = DEFAULT_SEED) -> List[dict]:
    """Every corner pass of every driver, session and lap, in driving order."""
    rng = random.Random(seed)
    rows = []
    for driver in DRIVERS:
        for session_number in range(1, SESSIONS_PER_DRIVER + 1):
            session_day = FIRST_SESSION_DATE + timedelta(days=DAYS_BETWEEN_SESSIONS * (session_number - 1))
            for lap in range(1, LAPS_PER_SESSION + 1):
                for corner in CORNERS:
                    rows.append(one_corner_pass(driver, session_number, session_day, lap, corner, rng))
    return rows


def driver_features(rows: List[dict]) -> List[dict]:
    """Per-driver summary numbers a clustering model would group on (anomalies left out)."""
    by_driver: Dict[str, List[dict]] = {}
    for row in rows:
        if not row["true_anomaly"]:
            by_driver.setdefault(row["driver_id"], []).append(row)
    features = []
    for driver_id, passes in by_driver.items():
        brakes = [p["brake_point_m"] for p in passes]
        grips = [p["grip_use"] for p in passes]
        features.append({
            "driver_id": driver_id, "driver_name": passes[0]["driver_name"],
            "mean_brake_point_m": round(mean(brakes), 2), "brake_point_spread_m": round(pstdev(brakes), 2),
            "mean_grip_use": round(mean(grips), 3), "grip_use_spread": round(pstdev(grips), 3),
            "corner_passes": len(passes), "true_style": passes[0]["true_style"],
        })
    return features


def write_csv(path: str, columns: List[str], rows: List[dict]) -> None:
    """Write rows to a CSV file with a SYNTHETIC warning as the first line."""
    with open(path, "w", newline="", encoding="utf-8") as handle:
        handle.write("# SYNTHETIC DEMO DATA - made up by ml_demo_data.py, not real drivers\n")
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None) -> None:
    """Generate both CSV files into the output folder and print what was written."""
    parser = argparse.ArgumentParser(description="Generate the SYNTHETIC ML demo data set.")
    parser.add_argument("--out", default=DEFAULT_OUT_DIR, help="Folder to write into")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Same seed, same data")
    args = parser.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)
    rows = generate_corner_rows(args.seed)
    features = driver_features(rows)
    write_csv(os.path.join(args.out, "corner_passes.csv"), CORNER_COLUMNS, rows)
    write_csv(os.path.join(args.out, "driver_features.csv"), list(features[0]), features)
    anomalies = sum(row["true_anomaly"] for row in rows)
    print(f"Wrote {len(rows)} corner passes ({anomalies} with an injected anomaly) "
          f"and {len(features)} driver summaries to {args.out}")


if __name__ == "__main__":
    main()
