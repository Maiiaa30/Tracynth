from io import StringIO

import pytest
from django.contrib.sessions.models import Session
from django.core.management import call_command
from django.core.management.base import CommandError

from accounts.models import User


@pytest.mark.django_db
def test_logout_all_sessions_increments_version_and_deletes_sessions(client, user):
    client.force_login(user)
    original_version = user.session_version
    assert Session.objects.exists()

    call_command("logout_all_sessions", stdout=StringIO())

    user.refresh_from_db()
    assert user.session_version == original_version + 1
    assert not Session.objects.exists()


@pytest.mark.django_db
def test_reset_operator_password_invalidates_sessions(client, user, monkeypatch):
    client.force_login(user)
    answers = iter(("A-new-strong-password-234!", "A-new-strong-password-234!"))
    monkeypatch.setattr(
        "accounts.management.commands.reset_operator_password.getpass",
        lambda _prompt: next(answers),
    )

    call_command("reset_operator_password", user.username, stdout=StringIO())

    user.refresh_from_db()
    assert user.check_password("A-new-strong-password-234!")
    assert not Session.objects.exists()


@pytest.mark.django_db
def test_create_initial_user_refuses_second_operator(user, monkeypatch):
    monkeypatch.setenv("TRACYNTH_INITIAL_USERNAME", "second")
    monkeypatch.setenv("TRACYNTH_INITIAL_PASSWORD", "A-new-strong-password-234!")
    with pytest.raises(CommandError, match="refusing to create another"):
        call_command("create_initial_user", stdout=StringIO())
    assert User.objects.count() == 1
