"""Vercel entry point: serves the Django app as a serverless function."""

import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
app = application


def _migrate_once():
    """Apply database migrations on the first start after a deploy (Vercel has no release step)."""
    from django.core.management import call_command
    from django.db import connection

    try:
        if connection.vendor == "postgresql":
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_lock(7351001)")  # one instance migrates at a time
            try:
                call_command("migrate", interactive=False, verbosity=0)
            finally:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_advisory_unlock(7351001)")
        else:
            call_command("migrate", interactive=False, verbosity=0)
    except Exception:
        logging.getLogger(__name__).exception("Automatic migration failed")


if os.environ.get("AUTO_MIGRATE", "1") == "1":
    _migrate_once()
