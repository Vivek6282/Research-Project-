"""
Trackside — IoT Reference Gateway Sync Implementation.

Demonstrates local buffer queueing (SQLite), backoff retries, and batch ingestion
POST /api/sessions/<id>/telemetry/ using Device Token Authentication.
"""

import time
import json
import sqlite3
import random
import urllib.request
import urllib.error
from datetime import datetime, timezone

# Reference Configuration
BACKEND_URL = "http://127.0.0.1:8000"
DEVICE_TOKEN = "demo_device_token_xyz123"
SESSION_ID = "00000000-0000-0000-0000-000000000000"
BATCH_SIZE = 25


def init_db(conn):
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS telemetry_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recorded_at TEXT,
                lateral_g REAL,
                speed_kmh REAL,
                gps_lat REAL,
                gps_lng REAL,
                status TEXT DEFAULT 'PENDING'
            )
        """
        )


def enqueue_reading(conn, lateral_g, speed_kmh, gps_lat, gps_lng):
    now_iso = datetime.now(timezone.utc).isoformat()
    with conn:
        conn.execute(
            """
            INSERT INTO telemetry_queue (recorded_at, lateral_g, speed_kmh, gps_lat, gps_lng)
            VALUES (?, ?, ?, ?, ?)
        """,
            (now_iso, lateral_g, speed_kmh, gps_lat, gps_lng),
        )


def get_pending_batch(conn, limit=BATCH_SIZE):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, recorded_at, lateral_g, speed_kmh, gps_lat, gps_lng FROM telemetry_queue WHERE status = 'PENDING' LIMIT ?",
        (limit,),
    )
    rows = cursor.fetchall()
    items = []
    ids = []
    for r in rows:
        ids.append(r[0])
        items.append(
            {
                "recorded_at": r[1],
                "lateral_g": r[2],
                "speed_kmh": r[3],
                "gps_lat": r[4],
                "gps_lng": r[5],
            }
        )
    return ids, items


def clear_batch(conn, ids):
    with conn:
        conn.executemany("DELETE FROM telemetry_queue WHERE id = ?", [(i,) for i in ids])


def sync_gateway():
    conn = sqlite3.connect(":memory:")
    init_db(conn)

    print("[GATEWAY] Enqueueing 50 simulated telemetry readings...")
    for i in range(50):
        g = round(0.8 + (i % 5) * 0.1, 2)
        spd = round(60 + (i % 10) * 3.5, 1)
        enqueue_reading(conn, g, spd, 11.016842, 76.955831)

    backoff = 2.0
    max_backoff = 60.0

    while True:
        ids, batch = get_pending_batch(conn)
        if not batch:
            print("[GATEWAY] Queue empty. All readings synced successfully.")
            break

        print(f"[GATEWAY] Attempting batch sync of {len(batch)} readings to backend...")
        url = f"{BACKEND_URL}/api/sessions/{SESSION_ID}/telemetry/"
        req = urllib.request.Request(
            url,
            data=json.dumps(batch).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Device-Token {DEVICE_TOKEN}",
            },
        )

        try:
            with urllib.request.urlopen(req) as resp:
                if resp.status == 201:
                    print(f"[GATEWAY] Batch synced! 201 Created.")
                    clear_batch(conn, ids)
                    backoff = 2.0  # Reset backoff
        except urllib.error.HTTPError as err:
            print(f"[GATEWAY] HTTP Error {err.code}: {err.reason}")
            if err.code == 401 or err.code == 403:
                print("[GATEWAY] Auth error — stopping retry loop.")
                break
            time.sleep(backoff)
            backoff = min(max_backoff, backoff * 2.0)
        except Exception as e:
            print(f"[GATEWAY] Network error: {e}. Retrying in {backoff}s...")
            time.sleep(backoff)
            backoff = min(max_backoff, backoff * 2.0)


if __name__ == "__main__":
    sync_gateway()
