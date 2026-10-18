import logging
import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from studio import scheduler

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Publish scheduled posts and run recurring rules and the content queue."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Run a single pass and exit (for cron).")
        parser.add_argument("--interval", type=int, default=30, help="Seconds between passes.")

    def handle(self, *args, once=False, interval=30, **options):
        self.stdout.write("Scheduler started.")
        while True:
            close_old_connections()
            try:
                scheduler.tick(budget_seconds=max(interval, 60))
            except Exception:  # keep the loop alive; individual failures are logged
                log.exception("Scheduler pass failed")
            if once:
                return
            time.sleep(interval)
