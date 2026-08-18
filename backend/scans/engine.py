from __future__ import annotations

import secrets
from collections.abc import Callable, Mapping
from datetime import timedelta
from typing import Any
from uuid import UUID

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from collectors import get_collector
from collectors.base.contract import (
    CollectionContext,
    Collector,
    CollectorResult,
    NetworkBudget,
    ResultStatus,
)
from collectors.network import CollectionCancelled, NetworkPolicyError

from .models import Scan, ScanModule

CollectorProvider = Callable[[str], Collector | None]
TERMINAL_SCAN_STATES = {Scan.State.SUCCEEDED, Scan.State.FAILED, Scan.State.CANCELLED}
TERMINAL_MODULE_STATES = {
    ScanModule.State.SUCCEEDED,
    ScanModule.State.FAILED,
    ScanModule.State.CANCELLED,
}


def _bounded_integer(value: object, default: int, minimum: int, maximum: int) -> int:
    if not isinstance(value, (str, bytes, bytearray, int, float)):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return min(max(parsed, minimum), maximum)


def _network_budget(scope: Mapping[str, Any]) -> NetworkBudget:
    configured = scope.get("network_budget", {})
    if not isinstance(configured, Mapping):
        configured = {}
    return NetworkBudget(
        max_requests=_bounded_integer(configured.get("max_requests"), 8, 1, 20),
        max_response_bytes=_bounded_integer(
            configured.get("max_response_bytes"), 512_000, 1024, 2_000_000
        ),
        request_timeout_seconds=_bounded_integer(
            configured.get("request_timeout_seconds"), 10, 1, 30
        ),
        max_redirects=_bounded_integer(configured.get("max_redirects"), 3, 0, 5),
    )


def _cancel_requested(scan_id: UUID) -> bool:
    return not Scan.objects.filter(pk=scan_id, cancellation_requested=False).exists()


def transition_to_cancelled(scan_id: UUID) -> bool:
    """Atomically make cancellation terminal for the scan and unfinished modules."""

    now = timezone.now()
    with transaction.atomic():
        changed = Scan.objects.filter(
            pk=scan_id, state__in=(Scan.State.QUEUED, Scan.State.RUNNING)
        ).update(
            cancellation_requested=True,
            state=Scan.State.CANCELLED,
            finished_at=now,
        )
        ScanModule.objects.filter(
            scan_id=scan_id,
            state__in=(ScanModule.State.PENDING, ScanModule.State.RUNNING),
        ).update(
            state=ScanModule.State.CANCELLED,
            progress=100,
            safe_error_code="collection_cancelled",
            finished_at=now,
        )
    return bool(changed)


def _claim_scan(scan_id: UUID) -> Scan | None:
    now = timezone.now()
    Scan.objects.filter(pk=scan_id, state=Scan.State.QUEUED).update(
        state=Scan.State.RUNNING,
        started_at=now,
    )
    scan = Scan.objects.filter(pk=scan_id).select_related("target").first()
    if scan is None or scan.state in TERMINAL_SCAN_STATES:
        return None
    if scan.cancellation_requested:
        transition_to_cancelled(scan_id)
        return None
    return scan


def _module_settings(scan: Scan, module_name: str) -> Mapping[str, Any]:
    configured = scan.scope_snapshot.get("collector_settings", {})
    if not isinstance(configured, Mapping):
        return {}
    module_settings = configured.get(module_name, {})
    return module_settings if isinstance(module_settings, Mapping) else {}


def _persist_result(scan: Scan, result: CollectorResult) -> None:
    from entities.models import Entity, Relationship
    from evidence.models import Evidence, RelationshipEvidence
    from findings.models import Finding, FindingEvidence

    entities: list[Entity] = []
    for entity_observation in result.entities:
        entity, _ = Entity.objects.update_or_create(
            entity_type=entity_observation.entity_type,
            normalized_value=entity_observation.normalized_value,
            defaults={"display_value": entity_observation.display_value},
        )
        entities.append(entity)

    evidence: list[Evidence] = []
    for evidence_index, evidence_observation in enumerate(result.evidence):
        linked_entity = next(
            (
                entities[entity_index]
                for entity_index, entity_observation in enumerate(result.entities)
                if evidence_index in entity_observation.evidence_indexes
            ),
            None,
        )
        evidence.append(
            Evidence.objects.create(
                scan=scan,
                target=scan.target,
                entity=linked_entity,
                collector_name=result.collector_name,
                collector_version=result.collector_version,
                source=evidence_observation.source,
                retrieved_at=evidence_observation.retrieved_at,
                confidence=evidence_observation.confidence,
                normalization_version=result.normalization_version,
                safe_excerpt=evidence_observation.safe_excerpt[:4000],
                artifact_reference=(
                    evidence_observation.artifact.storage_key
                    if evidence_observation.artifact
                    else ""
                ),
                content_sha256=(
                    evidence_observation.artifact.sha256 if evidence_observation.artifact else ""
                ),
            )
        )

    for relationship_observation in result.relationships:
        if (
            relationship_observation.source_entity_index
            == relationship_observation.target_entity_index
        ):
            continue
        relationship, _ = Relationship.objects.update_or_create(
            source=entities[relationship_observation.source_entity_index],
            target=entities[relationship_observation.target_entity_index],
            relationship_type=relationship_observation.relationship_type,
            defaults={"confidence": relationship_observation.confidence},
        )
        for evidence_index in relationship_observation.evidence_indexes:
            RelationshipEvidence.objects.get_or_create(
                relationship=relationship,
                evidence=evidence[evidence_index],
            )

    now = timezone.now()
    for finding_observation in result.findings:
        finding, _ = Finding.objects.update_or_create(
            scan=scan,
            affected_entity=entities[finding_observation.affected_entity_index],
            finding_type=finding_observation.finding_type,
            defaults={
                "title": finding_observation.title,
                "severity": finding_observation.severity,
                "confidence": finding_observation.confidence,
                "explanation": finding_observation.explanation,
                "remediation": finding_observation.remediation,
                "first_seen_at": now,
                "last_seen_at": now,
            },
        )
        for evidence_index in finding_observation.evidence_indexes:
            FindingEvidence.objects.get_or_create(
                finding=finding,
                evidence=evidence[evidence_index],
            )


def _finish_module(
    module: ScanModule,
    result: CollectorResult | None,
    state: str,
    safe_error_code: str = "",
) -> bool:
    now = timezone.now()
    with transaction.atomic():
        locked = ScanModule.objects.select_for_update().get(pk=module.pk)
        if locked.state != ScanModule.State.RUNNING:
            return False
        if result is not None:
            scan = Scan.objects.select_related("target").get(pk=module.scan_id)
            if scan.cancellation_requested:
                state = ScanModule.State.CANCELLED
                safe_error_code = "collection_cancelled"
            else:
                _persist_result(scan, result)
        locked.state = state
        locked.progress = 100
        locked.safe_error_code = safe_error_code
        locked.finished_at = now
        locked.save(update_fields=("state", "progress", "safe_error_code", "finished_at"))
    return True


def _run_module(
    scan: Scan,
    module: ScanModule,
    collector_provider: CollectorProvider,
) -> None:
    if scan.cancellation_requested or _cancel_requested(scan.id):
        transition_to_cancelled(scan.id)
        return
    now = timezone.now()
    claimed = ScanModule.objects.filter(pk=module.pk, state=ScanModule.State.PENDING).update(
        state=ScanModule.State.RUNNING,
        progress=5,
        started_at=now,
        safe_error_code="",
    )
    if not claimed and module.state != ScanModule.State.RUNNING:
        return
    collector = collector_provider(module.module)
    if collector is None:
        _finish_module(module, None, ScanModule.State.FAILED, "unsupported_module")
        return
    target_type = str(scan.scope_snapshot.get("target_type", scan.target.target_type))
    normalized_target = str(
        scan.scope_snapshot.get("normalized_value", scan.target.normalized_value)
    )
    context = CollectionContext(
        scan_id=scan.id,
        module_attempt_id=module.id,
        target_type=target_type,
        normalized_target=normalized_target,
        settings=_module_settings(scan, module.module),
        deadline=timezone.now() + timedelta(minutes=10),
        cancellation_requested=lambda: _cancel_requested(scan.id),
        network_budget=_network_budget(scan.scope_snapshot),
    )
    if not collector.can_run(context):
        _finish_module(module, None, ScanModule.State.FAILED, "unsupported_target_type")
        return
    try:
        result = collector.collect(context)
    except CollectionCancelled:
        _finish_module(module, None, ScanModule.State.CANCELLED, "collection_cancelled")
    except NetworkPolicyError:
        _finish_module(module, None, ScanModule.State.FAILED, "network_policy_blocked")
    except (TypeError, ValueError):
        _finish_module(module, None, ScanModule.State.FAILED, "collector_settings_invalid")
    except Exception:
        _finish_module(module, None, ScanModule.State.FAILED, "collector_failed")
    else:
        if result.status == ResultStatus.CANCELLED:
            _finish_module(module, None, ScanModule.State.CANCELLED, "collection_cancelled")
        else:
            warning = "partial_collection" if result.status == ResultStatus.PARTIAL else ""
            _finish_module(module, result, ScanModule.State.SUCCEEDED, warning)


def _finalize_scan(scan_id: UUID) -> None:
    scan = Scan.objects.filter(pk=scan_id).first()
    if scan is None or scan.state in TERMINAL_SCAN_STATES:
        return
    if scan.cancellation_requested:
        transition_to_cancelled(scan_id)
        return
    states = list(ScanModule.objects.filter(scan_id=scan_id).values_list("state", flat=True))
    if any(state not in TERMINAL_MODULE_STATES for state in states):
        return
    final_state = (
        Scan.State.FAILED
        if any(state == ScanModule.State.FAILED for state in states)
        else Scan.State.SUCCEEDED
    )
    Scan.objects.filter(pk=scan_id, state=Scan.State.RUNNING).update(
        state=final_state,
        finished_at=timezone.now(),
    )


def execute_scan(
    scan_id: str | UUID, collector_provider: CollectorProvider = get_collector
) -> None:
    parsed_id = UUID(str(scan_id))
    lock_key = f"scan-orchestrator:{parsed_id}"
    lock_token = secrets.token_urlsafe(18)
    if not cache.add(lock_key, lock_token, timeout=900):
        return
    try:
        scan = _claim_scan(parsed_id)
        if scan is None:
            return
        modules = list(ScanModule.objects.filter(scan=scan).order_by("created_at", "pk"))
        for module in modules:
            _run_module(scan, module, collector_provider)
            scan.refresh_from_db(fields=("state", "cancellation_requested"))
            if scan.cancellation_requested or scan.state == Scan.State.CANCELLED:
                transition_to_cancelled(scan.id)
                break
        _finalize_scan(scan.id)
    finally:
        if cache.get(lock_key) == lock_token:
            cache.delete(lock_key)


def mark_enqueue_failure(scan_id: str | UUID) -> None:
    parsed_id = UUID(str(scan_id))
    now = timezone.now()
    with transaction.atomic():
        ScanModule.objects.filter(scan_id=parsed_id, state=ScanModule.State.PENDING).update(
            state=ScanModule.State.FAILED,
            progress=100,
            safe_error_code="task_enqueue_failed",
            finished_at=now,
        )
        Scan.objects.filter(pk=parsed_id, state=Scan.State.QUEUED).update(
            state=Scan.State.FAILED,
            finished_at=now,
        )
