"""
Trackside — Guard for a known, unreachable Twisted issue (CVE-2026-106454).

The flaw is in Twisted's IMAP mail server code (twisted.mail.imap4). Trackside serves only HTTP and WebSockets
through Daphne and never loads that code. No fixed Twisted release exists yet. These tests fail if the app ever
starts using Twisted's mail code, which is the moment the issue would become reachable.
"""

import subprocess
import sys
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

PROJECT_ROOT = Path(settings.BASE_DIR).parent
SKIPPED_FOLDERS = {"node_modules", "venv", ".venv", "__pycache__", "dist", ".git"}


class TestTwistedMailCodeIsNotUsed(SimpleTestCase):

    def test_starting_the_app_does_not_load_twisted_mail(self):
        """Importing the real ASGI app (what Daphne serves) loads no twisted.mail module."""
        code = (
            "import os, sys, django\n"
            "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')\n"
            "django.setup()\n"
            "import config.asgi\n"
            "bad = sorted(m for m in sys.modules if m.startswith('twisted.mail'))\n"
            "print('LOADED:' + ','.join(bad))\n"
        )
        result = subprocess.run([sys.executable, "-c", code], cwd=settings.BASE_DIR,
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr[-500:])
        self.assertIn("LOADED:", result.stdout)
        self.assertEqual(result.stdout.strip().splitlines()[-1], "LOADED:")

    def test_no_project_code_imports_twisted_mail(self):
        """No Python file of the project imports twisted.mail or the imap4 module."""
        offenders = []
        for path in PROJECT_ROOT.rglob("*.py"):
            if SKIPPED_FOLDERS & set(path.parts) or path.name == Path(__file__).name:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "twisted.mail" in text or "imap4" in text:
                offenders.append(str(path.relative_to(PROJECT_ROOT)))
        self.assertEqual(offenders, [])
