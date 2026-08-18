from __future__ import annotations

import json
import socket
import ssl
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import urlsplit

from cryptography import x509
from cryptography.hazmat.primitives import hashes

from .base.contract import (
    CollectionContext,
    CollectorResult,
    EntityObservation,
    EvidenceObservation,
    FindingObservation,
    ResultStatus,
)
from .network import CollectionCancelled, Resolver, SystemResolver, resolve_public

TLSFetcher = Callable[[str, int, tuple[str, ...], float], bytes]


def _fetch_certificate_der(
    hostname: str, port: int, addresses: tuple[str, ...], timeout: float
) -> bytes:
    raw_socket = socket.create_connection((addresses[0], port), timeout=timeout)
    try:
        with ssl.create_default_context().wrap_socket(
            raw_socket, server_hostname=hostname
        ) as tls_socket:
            certificate = tls_socket.getpeercert(binary_form=True)
    finally:
        raw_socket.close()
    if not certificate:
        raise ssl.SSLError("peer_certificate_missing")
    return certificate


def _hostname_for(context: CollectionContext) -> str:
    if context.target_type == "url":
        return (urlsplit(context.normalized_target).hostname or "").rstrip(".").casefold()
    return context.normalized_target.rstrip(".").casefold()


class TLSCertificateCollector:
    name = "tls"
    version = "1.0.0"
    supported_target_types = frozenset({"domain", "url"})

    def __init__(
        self,
        resolver: Resolver | None = None,
        fetcher: TLSFetcher | None = None,
    ) -> None:
        self.resolver = resolver or SystemResolver()
        self.fetcher = fetcher or _fetch_certificate_der

    def validate_settings(self, settings: Mapping[str, Any]) -> Mapping[str, Any]:
        port = int(settings.get("port", 443))
        if port < 1 or port > 65535:
            raise ValueError("invalid_tls_port")
        timeout = min(max(float(settings.get("timeout_seconds", 8)), 0.1), 20.0)
        return {"port": port, "timeout_seconds": timeout}

    def can_run(self, context: CollectionContext) -> bool:
        return context.target_type in self.supported_target_types and bool(_hostname_for(context))

    def collect(self, context: CollectionContext) -> CollectorResult:
        if context.cancellation_requested():
            raise CollectionCancelled("collection_cancelled")
        settings = self.validate_settings(context.settings)
        hostname = _hostname_for(context)
        port = int(settings["port"])
        timeout = min(
            float(settings["timeout_seconds"]), context.network_budget.request_timeout_seconds
        )
        addresses = resolve_public(self.resolver, hostname, port)
        certificate_der = self.fetcher(hostname, port, addresses, timeout)
        if context.cancellation_requested():
            raise CollectionCancelled("collection_cancelled")
        certificate = x509.load_der_x509_certificate(certificate_der)
        now = datetime.now(UTC)
        try:
            sans = certificate.extensions.get_extension_for_class(
                x509.SubjectAlternativeName
            ).value.get_values_for_type(x509.DNSName)
        except x509.ExtensionNotFound:
            sans = []
        fingerprint = certificate.fingerprint(hashes.SHA256()).hex()
        metadata = {
            "subject": certificate.subject.rfc4514_string(),
            "issuer": certificate.issuer.rfc4514_string(),
            "serial_number": format(certificate.serial_number, "x"),
            "not_before": certificate.not_valid_before_utc.isoformat(),
            "not_after": certificate.not_valid_after_utc.isoformat(),
            "signature_algorithm": (
                certificate.signature_algorithm_oid._name
                or certificate.signature_algorithm_oid.dotted_string
            ),
            "sha256": fingerprint,
            "sans": sorted(sans)[:200],
        }
        evidence = (
            EvidenceObservation(
                source=f"tls://{hostname}:{port}",
                retrieved_at=now,
                confidence=Decimal("1.000"),
                safe_excerpt=json.dumps(metadata, sort_keys=True)[:4000],
            ),
        )
        entities = [EntityObservation("domain", hostname, hostname, (0,))]
        seen = {hostname}
        for san in sans:
            normalized = san.rstrip(".").casefold()
            if normalized and normalized not in seen:
                seen.add(normalized)
                entities.append(EntityObservation("domain", san, normalized, (0,)))
        findings: tuple[FindingObservation, ...] = ()
        if certificate.not_valid_after_utc <= now:
            findings = (
                FindingObservation(
                    affected_entity_index=0,
                    finding_type="tls_certificate_expired",
                    title="TLS certificate has expired",
                    severity="high",
                    confidence=Decimal("1.000"),
                    explanation="The certificate presented by the target is past its validity end.",
                    remediation="Renew and deploy a valid certificate.",
                    evidence_indexes=(0,),
                ),
            )
        return CollectorResult(
            self.name,
            self.version,
            "1",
            ResultStatus.SUCCEEDED,
            evidence,
            tuple(entities),
            findings=findings,
        )
