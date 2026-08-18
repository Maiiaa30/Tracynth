import os
from getpass import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError

from accounts.models import User


class Command(BaseCommand):
    help = "Create the first Tracynth operator without exposing a registration API."

    def add_arguments(self, parser):
        parser.add_argument("--username", default=os.getenv("TRACYNTH_INITIAL_USERNAME"))
        parser.add_argument("--email", default=os.getenv("TRACYNTH_INITIAL_EMAIL", ""))
        parser.add_argument("--password-env", default="TRACYNTH_INITIAL_PASSWORD")

    def handle(self, *args, **options):
        username = options["username"]
        password = os.getenv(options["password_env"])
        if not username:
            raise CommandError("Provide --username or set TRACYNTH_INITIAL_USERNAME.")
        if not password:
            password = getpass("Initial operator password: ")
            if password != getpass("Confirm password: "):
                raise CommandError("Passwords do not match.")
        if not password:
            raise CommandError("The initial password cannot be empty.")
        if User.objects.exists():
            raise CommandError(
                "A user already exists; refusing to create another initial operator."
            )
        candidate = User(
            username=username, email=options["email"], is_staff=True, is_superuser=True
        )
        validate_password(password, candidate)
        candidate.set_password(password)
        candidate.save()
        self.stdout.write(self.style.SUCCESS(f"Created initial operator {username!r}."))
