from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol
from urllib.parse import urlsplit

import dns.exception
import dns.resolver

from .base.contract import (
    CollectionContext,
    CollectorResult,
    EntityObservation,
    EvidenceObservation,
    ResultStatus,
)

RECORD_TYPES = ("A", "AAAA", "CNAME", "MX", "NS", "TXT", "CAA", "SOA")


class DNSLookup(Protocol):
    def query(self, name: str, record_type: str, lifetime: float) -> tuple[str, ...]: ...


class DnspythonLookup:
    def __init__(self) -> None:
        self._resolver = dns.resolver.Resolver(configure=True)

    def query(self, name: str, record_type: str, lifetime: float) -> tuple[str, ...]:
        answer = self._resolver.resolve(
            name,
            record_type,
            lifetime=lifetime,
            search=False,
            raise_on_no_answer=False,
        )
        if answer.rrset is None:
            return ()
        return tuple(record.to_text() for record in answer)


def _domain_for(context: CollectionContext) -> str:
    if context.target_type == "url":
        return (urlsplit(context.normalized_target).hostname or "").rstrip(".").casefold()
    return context.normalized_target.rstrip(".").casefold()


def _unquote_txt(value: str) -> str:
    parts = value.split('"')
    if len(parts) >= 3:
        return "".join(parts[1::2])
    return value


class DNSCollector:
    name = "dns"
    version = "1.0.0"
    supported_target_types = frozenset({"domain", "url"})

    def __init__(self, lookup: DNSLookup | None = None) -> None:
        self.lookup = lookup or DnspythonLookup()

    def validate_settings(self, settings: Mapping[str, Any]) -> Mapping[str, Any]:
        timeout = float(settings.get("timeout_seconds", 5))
        return {"timeout_seconds": min(max(timeout, 0.1), 15.0)}

    def can_run(self, context: CollectionContext) -> bool:
        return context.target_type in self.supported_target_types and bool(_domain_for(context))

    def collect(self, context: CollectionContext) -> CollectorResult:
        settings = self.validate_settings(context.settings)
        timeout = min(
            float(settings["timeout_seconds"]), context.network_budget.request_timeout_seconds
        )
        domain = _domain_for(context)
        retrieved_at = datetime.now(UTC)
        evidence: list[EvidenceObservation] = []
        entities = [EntityObservation("domain", domain, domain)]
        entity_keys = {("domain", domain): 0}
        warnings: list[str] = []

        def add_entity(entity_type: str, value: str, evidence_index: int) -> None:
            normalized = value.rstrip(".").casefold()
            key = (entity_type, normalized)
            if key in entity_keys:
                return
            entity_keys[key] = len(entities)
            entities.append(
                EntityObservation(entity_type, normalized, normalized, (evidence_index,))
            )

        for record_type in RECORD_TYPES:
            if context.cancellation_requested() or datetime.now(UTC) >= context.deadline:
                return CollectorResult(
                    self.name,
                    self.version,
                    "1",
                    ResultStatus.CANCELLED,
                    evidence,
                    entities,
                    safe_warnings=("collection_cancelled",),
                )
            try:
                values = self.lookup.query(domain, record_type, timeout)
            except (dns.resolver.NXDOMAIN, dns.resolver.NoNameservers, dns.exception.Timeout):
                warnings.append(f"dns_{record_type.casefold()}_lookup_failed")
                continue
            except dns.resolver.NoAnswer:
                values = ()
            for value in values:
                safe_value = value[:1000]
                evidence_index = len(evidence)
                evidence.append(
                    EvidenceObservation(
                        source=f"dns://{domain}/{record_type}",
                        retrieved_at=retrieved_at,
                        confidence=Decimal("1.000"),
                        safe_excerpt=f"{record_type} {safe_value}",
                    )
                )
                if record_type in {"A", "AAAA"}:
                    add_entity("ip_address", value, evidence_index)
                elif record_type in {"CNAME", "NS"}:
                    add_entity("domain", value, evidence_index)
                elif record_type == "MX":
                    exchange = value.split()[-1] if value.split() else value
                    add_entity("domain", exchange, evidence_index)
                elif record_type == "TXT":
                    text = _unquote_txt(value)
                    if text.casefold().startswith("v=spf1"):
                        evidence.append(
                            EvidenceObservation(
                                source=f"dns://{domain}/SPF",
                                retrieved_at=retrieved_at,
                                confidence=Decimal("1.000"),
                                safe_excerpt=f"SPF {text[:1000]}",
                            )
                        )

        try:
            dmarc_values = self.lookup.query(f"_dmarc.{domain}", "TXT", timeout)
        except (dns.exception.DNSException, OSError):
            warnings.append("dmarc_lookup_failed")
        else:
            for value in dmarc_values:
                text = _unquote_txt(value)
                if text.casefold().startswith("v=dmarc1"):
                    evidence.append(
                        EvidenceObservation(
                            source=f"dns://_dmarc.{domain}/TXT",
                            retrieved_at=retrieved_at,
                            confidence=Decimal("1.000"),
                            safe_excerpt=f"DMARC {text[:1000]}",
                        )
                    )

        return CollectorResult(
            self.name,
            self.version,
            "1",
            ResultStatus.PARTIAL if warnings else ResultStatus.SUCCEEDED,
            tuple(evidence),
            tuple(entities),
            safe_warnings=tuple(warnings),
        )
