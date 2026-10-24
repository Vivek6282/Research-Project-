"""
Trackside — Guard for known Twisted issues in code Trackside never loads.

- CVE-2026-106454, CVE-2026-115774: IMAP mail server (twisted.mail)
- CVE-2026-115778: telnet (twisted.conch)
- CVE-2026-115776: IRC server (twisted.words)
- CVE-2026-115775: XML streams (twisted.words.xish)

Trackside serves only HTTP and WebSockets through Daphne. These tests fail if the app ever starts loading
one of these parts, which is the moment the issue would become reachable. (CVE-2026-115877 is in the HTTP
server Daphne does use; see the note in requirements.txt.)
"""

import subprocess
import sys
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

PROJECT_ROOT = Path(settings.BASE_DIR).parent
SKIPPED_FOLDERS = {"node_modules", "venv", ".venv", "__pycache__", "dist", ".git"}


UNUSED_TWISTED_PARTS = ("twisted.mail", "twisted.conch", "twisted.words")


class TestTwistedMailCodeIsNotUsed(SimpleTestCase):

    def test_starting_the_app_does_not_load_twisted_mail(self):
        """Importing the real ASGI app (what Daphne serves) loads no twisted mail, telnet, IRC or XML-stream module."""
        code = (
            "import os, sys, django\n"
            "os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')\n"
            "django.setup()\n"
            "import config.asgi\n"
            f"bad = sorted(m for m in sys.modules if m.startswith({UNUSED_TWISTED_PARTS!r}))\n"
            "print('LOADED:' + ','.join(bad))\n"
        )
        result = subprocess.run([sys.executable, "-c", code], cwd=settings.BASE_DIR,
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr[-500:])
        self.assertIn("LOADED:", result.stdout)
        self.assertEqual(result.stdout.strip().splitlines()[-1], "LOADED:")

    def test_no_project_code_imports_twisted_mail(self):
        """No Python file of the project imports those Twisted parts."""
        offenders = []
        for path in PROJECT_ROOT.rglob("*.py"):
            if SKIPPED_FOLDERS & set(path.parts) or path.name == Path(__file__).name:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "imap4" in text or any(part in text for part in UNUSED_TWISTED_PARTS):
                offenders.append(str(path.relative_to(PROJECT_ROOT)))
        self.assertEqual(offenders, [])
