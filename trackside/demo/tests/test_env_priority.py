"""
Unit test: variables already in the environment beat trackside/demo/.env (H4).
A Coach demo run passes SESSION_ID, DEVICE_TOKEN, BACKEND_URL and DEMO_ZONES as
environment variables; a stale .env must never override them.
"""

import os
import subprocess
import sys
import tempfile
import textwrap
import unittest

DEMO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class EnvPriorityTests(unittest.TestCase):
    """Run sim_config in a clean child process next to a throw-away .env file."""

    def test_environment_values_beat_the_env_file_and_the_file_fills_the_rest(self):
        """SESSION_ID from the environment wins; SERIAL_PORT (only in .env) is still read."""
        with tempfile.TemporaryDirectory() as folder:
            for name in ("sim_config.py",):
                with open(os.path.join(DEMO_DIR, name), encoding="utf-8") as src, open(os.path.join(folder, name), "w", encoding="utf-8") as dst:
                    dst.write(src.read())
            with open(os.path.join(folder, ".env"), "w", encoding="utf-8") as handle:
                handle.write("SESSION_ID=from-dotenv\nDEVICE_TOKEN=stale-token\nSERIAL_PORT=COM9\n")
            code = textwrap.dedent("""
                import sim_config
                print(sim_config.SESSION_ID, sim_config.DEVICE_TOKEN, sim_config.SERIAL_PORT)
            """)
            env = {k: v for k, v in os.environ.items() if k not in ("SESSION_ID", "DEVICE_TOKEN", "SERIAL_PORT")}
            env.update({"SESSION_ID": "from-environment", "DEVICE_TOKEN": "fresh-token"})
            result = subprocess.run([sys.executable, "-I", "-c", f"import sys; sys.path.insert(0, {folder!r}); {code}"],
                                    env=env, capture_output=True, text=True, cwd=folder)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.split(), ["from-environment", "fresh-token", "COM9"])


if __name__ == "__main__":
    unittest.main()
