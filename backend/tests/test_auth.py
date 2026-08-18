import pytest
from django.contrib.auth.hashers import identify_hasher
from django.core.cache import cache
from django.test import Client, override_settings

from accounts.models import AuditEvent, User


def csrf_client():
    client = Client(enforce_csrf_checks=True)
    response = client.get("/api/v1/auth/csrf/")
    assert response.status_code == 200
    return client, response.cookies["tracynth_csrftoken"].value


@pytest.mark.django_db
def test_login_requires_csrf(user, password):
    client = Client(enforce_csrf_checks=True)
    response = client.post(
        "/api/v1/auth/login/",
        {"username": user.username, "password": password},
        content_type="application/json",
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"


def test_unknown_api_route_uses_stable_json_error():
    response = Client().get("/api/v1/unsupported-resource/")
    assert response.status_code == 404
    assert response.headers["Content-Type"].startswith("application/json")
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.django_db
def test_login_me_logout_and_argon2(user, password):
    client, token = csrf_client()
    response = client.post(
        "/api/v1/auth/login/",
        {"username": user.username, "password": password},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == 200
    assert identify_hasher(User.objects.get(pk=user.pk).password).algorithm == "argon2"
    assert client.get("/api/v1/auth/me/").status_code == 200
    assert AuditEvent.objects.filter(event_type="auth.login", outcome="success").exists()

    token = client.cookies["tracynth_csrftoken"].value
    response = client.post("/api/v1/auth/logout/", HTTP_X_CSRFTOKEN=token)
    assert response.status_code == 204
    assert client.get("/api/v1/auth/me/").status_code == 403


@pytest.mark.django_db
@override_settings(LOGIN_BACKOFF_THRESHOLD=2, LOGIN_BACKOFF_BASE_SECONDS=10)
def test_login_backoff_is_bounded_and_does_not_reveal_account(user):
    cache.clear()
    client, token = csrf_client()
    payload = {"username": user.username, "password": "wrong"}
    first = client.post(
        "/api/v1/auth/login/", payload, content_type="application/json", HTTP_X_CSRFTOKEN=token
    )
    second = client.post(
        "/api/v1/auth/login/", payload, content_type="application/json", HTTP_X_CSRFTOKEN=token
    )
    third = client.post(
        "/api/v1/auth/login/", payload, content_type="application/json", HTTP_X_CSRFTOKEN=token
    )
    assert first.status_code == 401
    assert first.json()["error"]["code"] == "invalid_credentials"
    assert second.status_code == 401
    assert "Retry-After" in second
    assert third.status_code == 429
    assert third.json()["error"]["code"] == "login_backoff"


@pytest.mark.django_db
@override_settings(
    LOGIN_BACKOFF_THRESHOLD=20,
    LOGIN_GLOBAL_BACKOFF_THRESHOLD=2,
    LOGIN_BACKOFF_BASE_SECONDS=10,
)
def test_login_backoff_cannot_be_evaded_by_rotating_usernames(user):
    cache.clear()
    client, token = csrf_client()
    for username in ("first-guess", "second-guess"):
        response = client.post(
            "/api/v1/auth/login/",
            {"username": username, "password": "wrong"},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        assert response.status_code == 401
    blocked = client.post(
        "/api/v1/auth/login/",
        {"username": "third-guess", "password": "wrong"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert blocked.status_code == 429


@pytest.mark.django_db
def test_logout_all_invalidates_other_sessions(user, password):
    first, token_one = csrf_client()
    second, token_two = csrf_client()
    credentials = {"username": user.username, "password": password}
    assert (
        first.post(
            "/api/v1/auth/login/",
            credentials,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token_one,
        ).status_code
        == 200
    )
    assert (
        second.post(
            "/api/v1/auth/login/",
            credentials,
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token_two,
        ).status_code
        == 200
    )
    response = first.post(
        "/api/v1/auth/logout-all/", HTTP_X_CSRFTOKEN=first.cookies["tracynth_csrftoken"].value
    )
    assert response.status_code == 204
    assert second.get("/api/v1/auth/me/").status_code == 403


@pytest.mark.django_db
def test_password_change_keeps_current_session_and_rehashes(user, password):
    client, token = csrf_client()
    assert (
        client.post(
            "/api/v1/auth/login/",
            {"username": user.username, "password": password},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        ).status_code
        == 200
    )
    new_password = "A-New-Correct-Horse-Battery-948!"
    response = client.post(
        "/api/v1/auth/password/",
        {"current_password": password, "new_password": new_password},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=client.cookies["tracynth_csrftoken"].value,
    )
    assert response.status_code == 200
    assert client.get("/api/v1/auth/me/").status_code == 200
    user.refresh_from_db()
    assert user.check_password(new_password)
    assert not user.check_password(password)
