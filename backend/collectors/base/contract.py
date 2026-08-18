from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Protocol
from uuid import UUID


class ResultStatus(StrEnum):
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class CollectionContext:
    scan_id: UUID
    module_attempt_id: UUID
    target_type: str
    normalized_target: str
    settings: Mapping[str, Any]
    deadline: datetime
    cancellation_requested: Callable[[], bool]
    network_budget: NetworkBudget


@dataclass(frozen=True, slots=True)
class NetworkBudget:
    max_requests: int
    max_response_bytes: int
    request_timeout_seconds: int
    max_redirects: int


@dataclass(frozen=True, slots=True)
class ArtifactReference:
    storage_key: str
    sha256: str
    size_bytes: int
    mime_type: str


@dataclass(frozen=True, slots=True)
class EvidenceObservation:
    source: str
    retrieved_at: datetime
    confidence: Decimal
    safe_excerpt: str = ""
    artifact: ArtifactReference | None = None


@dataclass(frozen=True, slots=True)
class EntityObservation:
    entity_type: str
    display_value: str
    normalized_value: str
    evidence_indexes: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class RelationshipObservation:
    source_entity_index: int
    target_entity_index: int
    relationship_type: str
    confidence: Decimal
    evidence_indexes: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class FindingObservation:
    affected_entity_index: int
    finding_type: str
    title: str
    severity: str
    confidence: Decimal
    explanation: str
    remediation: str = ""
    evidence_indexes: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class CollectorResult:
    collector_name: str
    collector_version: str
    normalization_version: str
    status: ResultStatus
    evidence: Sequence[EvidenceObservation] = field(default_factory=tuple)
    entities: Sequence[EntityObservation] = field(default_factory=tuple)
    relationships: Sequence[RelationshipObservation] = field(default_factory=tuple)
    findings: Sequence[FindingObservation] = field(default_factory=tuple)
    safe_warnings: Sequence[str] = field(default_factory=tuple)


class Collector(Protocol):
    name: str
    version: str
    supported_target_types: frozenset[str]

    def validate_settings(self, settings: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def can_run(self, context: CollectionContext) -> bool: ...

    def collect(self, context: CollectionContext) -> CollectorResult:
        """Collect passively without writing models or returning secrets."""
        ...
