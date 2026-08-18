from getpass import getpass

from django.contrib.auth.password_validation import validate_password
from django.contrib.sessions.models import Session
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import AuditEvent, User


class Command(BaseCommand):
    help = "Interactively reset the single operator password and invalidate all sessions."

    def add_arguments(self, parser):
        parser.add_argument("username", nargs="?")

    def handle(self, *args, **options):
        queryset = User.objects.all()
        username = options.get("username")
        if username:
            queryset = queryset.filter(username=username)
        users = list(queryset[:2])
        if len(users) != 1:
            raise CommandError("Exactly one matching operator is required.")
        user = users[0]
        password = getpass("New operator password: ")
        if password != getpass("Confirm password: "):
            raise CommandError("Passwords do not match.")
        validate_password(password, user)
        with transaction.atomic():
            locked = User.objects.select_for_update().get(pk=user.pk)
            locked.set_password(password)
            locked.session_version += 1
            locked.save(update_fields=("password", "session_version"))
            Session.objects.all().delete()
            AuditEvent.objects.create(
                actor=locked,
                event_type="auth.password_reset",
                metadata={"source": "cli"},
            )
        self.stdout.write(self.style.SUCCESS(f"Reset password for {user.username!r}."))
