import pytest
from django.core.exceptions import ValidationError

from targets.validators import validate_public_http_url


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/admin",
        "http://10.0.0.1/",
        "http://2130706433/",
        "http://[::1]/",
        "http://localhost/",
        "https://user:password@example.com/",
        "file:///etc/passwd",
    ],
)
def test_ssrf_validator_rejects_unsafe_destinations(url):
    with pytest.raises(ValidationError):
        validate_public_http_url(url)


def test_ssrf_validator_accepts_public_http_url():
    validate_public_http_url("https://example.com/path?q=1")


def test_public_ipv6_url_normalization_stays_valid():
    from targets.validators import normalize_target

    value = "https://[2001:4860:4860::8888]/dns-query"
    normalized = normalize_target("url", value)
    assert normalized == value
    validate_public_http_url(normalized)


@pytest.mark.parametrize("domain", ["localhost", "service.local", "127.0.0.1", "not a domain"])
def test_domain_target_rejects_local_or_invalid_names(domain):
    from targets.validators import validate_public_domain

    with pytest.raises(ValidationError):
        validate_public_domain(domain)


@pytest.mark.django_db
def test_authenticated_target_collection_is_paginated(client, user):
    client.force_login(user)
    response = client.get("/api/v1/targets/")
    assert response.status_code == 200
    assert set(response.json()) == {"count", "next", "previous", "results"}
