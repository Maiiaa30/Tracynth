from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F

from accounts.models import AuditEvent, User


class Command(BaseCommand):
    help = "Invalidate every Tracynth application session."

    def handle(self, *args, **options):
        with transaction.atomic():
            User.objects.update(session_version=F("session_version") + 1)
            deleted, _ = Session.objects.all().delete()
            AuditEvent.objects.create(event_type="auth.logout_all", metadata={"source": "cli"})
        self.stdout.write(self.style.SUCCESS(f"Invalidated all sessions ({deleted} rows)."))
