from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from collectors.base.contract import CollectionContext, NetworkBudget, ResultStatus
from collectors.dns import DNSCollector
from collectors.network import InvalidDestination, ResponseLimitExceeded, SSRFSafeHTTPClient
from collectors.tls import TLSCertificateCollector
from collectors.web import WebStandardEndpointsCollector


class FakeResolver:
    def __init__(self, addresses: tuple[str, ...] = ("93.184.216.34",)) -> None:
        self.addresses = addresses
        self.calls: list[tuple[str, int]] = []

    def resolve(self, hostname: str, port: int) -> tuple[str, ...]:
        self.calls.append((hostname, port))
        return self.addresses


class FakeDNS:
    answers = {
        ("example.com", "A"): ("93.184.216.34",),
        ("example.com", "AAAA"): ("2606:2800:220:1:248:1893:25c8:1946",),
        ("example.com", "CNAME"): (),
        ("example.com", "MX"): ("10 mail.example.com.",),
        ("example.com", "NS"): ("ns1.example.net.",),
        ("example.com", "TXT"): ('"v=spf1 -all"',),
        ("example.com", "CAA"): ('0 issue "letsencrypt.org"',),
        ("example.com", "SOA"): ("ns1.example.net. hostmaster.example.com. 1 2 3 4 5",),
        ("_dmarc.example.com", "TXT"): ('"v=DMARC1; p=reject"',),
    }

    def query(self, name: str, record_type: str, lifetime: float) -> tuple[str, ...]:
        assert 0 < lifetime <= 15
        return self.answers[(name, record_type)]


def collection_context(cancelled=lambda: False) -> CollectionContext:
    return CollectionContext(
        scan_id=uuid4(),
        module_attempt_id=uuid4(),
        target_type="domain",
        normalized_target="example.com",
        settings={},
        deadline=datetime.now(UTC) + timedelta(minutes=1),
        cancellation_requested=cancelled,
        network_budget=NetworkBudget(8, 4096, 5, 2),
    )


def test_dns_collector_returns_records_and_mail_observations():
    result = DNSCollector(lookup=FakeDNS()).collect(collection_context())

    assert result.status == ResultStatus.SUCCEEDED
    assert {e.source.rsplit("/", 1)[-1] for e in result.evidence} >= {
        "A",
        "AAAA",
        "MX",
        "SPF",
        "TXT",
    }
    assert any(e.safe_excerpt.startswith("DMARC ") for e in result.evidence)
    assert {entity.entity_type for entity in result.entities} == {"domain", "ip_address"}


def test_http_policy_rejects_any_non_public_dns_answer():
    resolver = FakeResolver(("93.184.216.34", "127.0.0.1"))
    client = SSRFSafeHTTPClient(
        resolver=resolver,
        max_requests=1,
        max_response_bytes=1024,
        timeout_seconds=1,
        max_redirects=0,
        cancellation_requested=lambda: False,
        transport=httpx.MockTransport(lambda request: httpx.Response(200, text="unused")),
    )
    with client, pytest.raises(InvalidDestination, match="non_public_destination"):
        client.get("https://example.com/")


def test_http_policy_revalidates_redirect_destination():
    resolver = FakeResolver()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "http://127.0.0.1/latest/meta-data/"})

    client = SSRFSafeHTTPClient(
        resolver=resolver,
        max_requests=2,
        max_response_bytes=1024,
        timeout_seconds=1,
        max_redirects=1,
        cancellation_requested=lambda: False,
        transport=httpx.MockTransport(handler),
    )
    with client, pytest.raises(InvalidDestination, match="non_public_destination"):
        client.get("https://example.com/")


def test_http_policy_enforces_streamed_byte_limit():
    client = SSRFSafeHTTPClient(
        resolver=FakeResolver(),
        max_requests=1,
        max_response_bytes=4,
        timeout_seconds=1,
        max_redirects=0,
        cancellation_requested=lambda: False,
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"12345")),
    )
    with client, pytest.raises(ResponseLimitExceeded, match="response_too_large"):
        client.get("https://example.com/")


def test_tls_collector_uses_validated_pinned_address_and_parses_metadata():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "example.com")])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(42)
        .not_valid_before(datetime.now(UTC) - timedelta(days=1))
        .not_valid_after(datetime.now(UTC) + timedelta(days=30))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("www.example.com")]), False)
        .sign(key, hashes.SHA256())
    )
    der = certificate.public_bytes(serialization.Encoding.DER)
    observed: list[tuple[str, int, tuple[str, ...]]] = []

    def fetcher(hostname: str, port: int, addresses: tuple[str, ...], timeout: float) -> bytes:
        observed.append((hostname, port, addresses))
        return der

    result = TLSCertificateCollector(resolver=FakeResolver(), fetcher=fetcher).collect(
        collection_context()
    )

    assert observed == [("example.com", 443, ("93.184.216.34",))]
    assert result.status == ResultStatus.SUCCEEDED
    assert "signature_algorithm" in result.evidence[0].safe_excerpt
    assert {entity.normalized_value for entity in result.entities} == {
        "example.com",
        "www.example.com",
    }


def test_web_collector_uses_bounded_mocked_httpx_requests():
    def handler(request: httpx.Request) -> httpx.Response:
        bodies = {
            "/": "<title>Example</title><meta name='description' content='Test site'>",
            "/robots.txt": "User-agent: *\nDisallow:",
            "/sitemap.xml": "<urlset />",
            "/.well-known/security.txt": "Contact: mailto:security@example.com",
        }
        return httpx.Response(
            200 if request.url.path in bodies else 404, text=bodies.get(request.url.path, "")
        )

    def client_factory(context: CollectionContext) -> SSRFSafeHTTPClient:
        return SSRFSafeHTTPClient(
            resolver=FakeResolver(),
            max_requests=context.network_budget.max_requests,
            max_response_bytes=context.network_budget.max_response_bytes,
            timeout_seconds=context.network_budget.request_timeout_seconds,
            max_redirects=context.network_budget.max_redirects,
            cancellation_requested=context.cancellation_requested,
            transport=httpx.MockTransport(handler),
        )

    result = WebStandardEndpointsCollector(client_factory=client_factory).collect(
        collection_context()
    )

    assert result.status == ResultStatus.SUCCEEDED
    assert len(result.evidence) == 4
    assert "title=Example" in result.evidence[0].safe_excerpt
    assert "https://example.com/security.txt" not in {
        evidence.source for evidence in result.evidence
    }
