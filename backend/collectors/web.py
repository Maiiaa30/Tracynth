from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from decimal import Decimal
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlsplit

from .base.contract import (
    CollectionContext,
    CollectorResult,
    EntityObservation,
    EvidenceObservation,
    ResultStatus,
)
from .network import (
    CollectionCancelled,
    InvalidDestination,
    Resolver,
    ResponseLimitExceeded,
    SSRFSafeHTTPClient,
)


class _MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.description = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key.casefold(): value or "" for key, value in attrs}
        if tag.casefold() == "title":
            self._in_title = True
        if tag.casefold() == "meta" and attributes.get("name", "").casefold() == "description":
            self.description = attributes.get("content", "")

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data


def _safe_text(value: str, limit: int = 2000) -> str:
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value).strip()[:limit]


HTTPClientFactory = Callable[[CollectionContext], SSRFSafeHTTPClient]


class WebStandardEndpointsCollector:
    name = "web"
    version = "1.0.0"
    supported_target_types = frozenset({"domain", "url"})

    def __init__(
        self,
        resolver: Resolver | None = None,
        client_factory: HTTPClientFactory | None = None,
    ) -> None:
        self.resolver = resolver
        self.client_factory = client_factory

    def validate_settings(self, settings: Mapping[str, Any]) -> Mapping[str, Any]:
        preferred_scheme = str(settings.get("preferred_scheme", "https")).casefold()
        if preferred_scheme not in {"http", "https"}:
            raise ValueError("invalid_preferred_scheme")
        return {"preferred_scheme": preferred_scheme}

    def can_run(self, context: CollectionContext) -> bool:
        return context.target_type in self.supported_target_types

    def _client(self, context: CollectionContext) -> SSRFSafeHTTPClient:
        if self.client_factory is not None:
            return self.client_factory(context)
        budget = context.network_budget
        return SSRFSafeHTTPClient(
            resolver=self.resolver,
            max_requests=budget.max_requests,
            max_response_bytes=budget.max_response_bytes,
            timeout_seconds=budget.request_timeout_seconds,
            max_redirects=budget.max_redirects,
            cancellation_requested=context.cancellation_requested,
        )

    def collect(self, context: CollectionContext) -> CollectorResult:
        settings = self.validate_settings(context.settings)
        if context.target_type == "url":
            parsed = urlsplit(context.normalized_target)
            base = f"{parsed.scheme}://{parsed.netloc}"
            homepage = context.normalized_target
            hostname = parsed.hostname or ""
        else:
            hostname = context.normalized_target.rstrip(".")
            base = f"{settings['preferred_scheme']}://{hostname}"
            homepage = f"{base}/"
        endpoints = (
            ("homepage", homepage),
            ("robots", f"{base}/robots.txt"),
            ("sitemap", f"{base}/sitemap.xml"),
            ("security_txt", f"{base}/.well-known/security.txt"),
            ("security_txt_fallback", f"{base}/security.txt"),
        )
        retrieved_at = datetime.now(UTC)
        evidence: list[EvidenceObservation] = []
        warnings: list[str] = []
        well_known_security_found = False
        with self._client(context) as client:
            for endpoint_name, url in endpoints:
                if endpoint_name == "security_txt_fallback" and well_known_security_found:
                    continue
                try:
                    response = client.get(url)
                except CollectionCancelled:
                    return CollectorResult(
                        self.name,
                        self.version,
                        "1",
                        ResultStatus.CANCELLED,
                        tuple(evidence),
                        (EntityObservation("domain", hostname, hostname),),
                        safe_warnings=("collection_cancelled",),
                    )
                except (InvalidDestination, ResponseLimitExceeded):
                    warnings.append(f"{endpoint_name}_collection_failed")
                    continue
                if response.status_code >= 400:
                    continue
                if endpoint_name == "security_txt":
                    well_known_security_found = True
                excerpt = _safe_text(response.text)
                if endpoint_name == "homepage":
                    parser = _MetadataParser()
                    parser.feed(response.text[:100_000])
                    excerpt = _safe_text(
                        f"title={parser.title.strip()} description={parser.description.strip()}"
                    )
                evidence.append(
                    EvidenceObservation(
                        source=response.url,
                        retrieved_at=retrieved_at,
                        confidence=Decimal("1.000"),
                        safe_excerpt=f"HTTP {response.status_code} {excerpt}",
                    )
                )
        return CollectorResult(
            self.name,
            self.version,
            "1",
            ResultStatus.PARTIAL if warnings else ResultStatus.SUCCEEDED,
            tuple(evidence),
            (EntityObservation("domain", hostname, hostname, tuple(range(len(evidence)))),),
            safe_warnings=tuple(warnings),
        )
