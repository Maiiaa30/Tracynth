import pytest
from django.test import override_settings

from config.checks import production_configuration_check


@pytest.mark.django_db
def test_health_is_public_and_non_sensitive(client):
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_api_requires_authentication(client):
    response = client.get("/api/v1/targets/")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_authenticated"
    assert "results" not in response.json()


@override_settings(ENVIRONMENT="development", SESSION_COOKIE_SECURE=False)
def test_development_check_allows_insecure_loopback_cookie():
    errors = production_configuration_check(None)
    assert all(error.id != "tracynth.E002" for error in errors)


@override_settings(ENVIRONMENT="production", SESSION_COOKIE_SECURE=False)
def test_production_check_requires_secure_cookie():
    errors = production_configuration_check(None)
    assert any(error.id == "tracynth.E002" for error in errors)
