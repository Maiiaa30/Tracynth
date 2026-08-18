import pytest


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
