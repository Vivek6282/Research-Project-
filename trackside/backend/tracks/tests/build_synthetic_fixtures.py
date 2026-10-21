"""
Trackside — Writes the synthetic fixture files used by the import tests.

Run from the backend folder:  python tracks/tests/build_synthetic_fixtures.py
The files are SYNTHETIC (see their first line); they are not real recordings.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import synthetic_track as st  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def main():
    """Write the CSV and VBO fixtures next to this script."""
    samples = st.make_samples(laps=3)
    with open(os.path.join(FIXTURES, "synthetic_racechrono_v3.csv"), "w", newline="") as handle:
        handle.write(st.racechrono_csv_text(samples))
    with open(os.path.join(FIXTURES, "synthetic_track.vbo"), "w", newline="") as handle:
        handle.write(st.vbo_text(samples[: len(samples) // 3 * 2]))
    print("lap length (m):", round(st.lap_length(), 1))


if __name__ == "__main__":
    main()
