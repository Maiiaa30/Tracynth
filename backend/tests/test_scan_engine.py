from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from collectors.base.contract import (
    CollectionContext,
    CollectorResult,
    EntityObservation,
    EvidenceObservation,
    ResultStatus,
)
from evidence.models import Evidence
from scans.engine import execute_scan, transition_to_cancelled
from scans.models import Scan, ScanModule
from targets.models import ScanConfiguration, Target


class SuccessfulCollector:
    name = "test"
    version = "1.0"
    supported_target_types = frozenset({"domain"})

    def validate_settings(self, settings):
        return settings

    def can_run(self, context: CollectionContext) -> bool:
        return True

    def collect(self, context: CollectionContext) -> CollectorResult:
        return CollectorResult(
            self.name,
            self.version,
            "1",
            ResultStatus.SUCCEEDED,
            evidence=(
                EvidenceObservation(
                    source="mock://test",
                    retrieved_at=datetime.now(UTC),
                    confidence=Decimal("1.000"),
                    safe_excerpt="deterministic",
                ),
            ),
            entities=(EntityObservation("domain", "example.com", "example.com", (0,)),),
        )


@pytest.fixture
def domain_target(db, user):
    return Target.objects.create(
        target_type=Target.Type.DOMAIN,
        display_value="example.com",
        created_by=user,
    )


def make_scan(domain_target, modules: tuple[str, ...]) -> Scan:
    scan = Scan.objects.create(
        target=domain_target,
        scope_snapshot={
            "target_type": "domain",
            "normalized_value": "example.com",
            "collector_settings": {},
        },
    )
    ScanModule.objects.bulk_create(
        ScanModule(scan=scan, module=module, attempt=1) for module in modules
    )
    return scan


@pytest.mark.django_db
def test_engine_reaches_terminal_state_and_is_idempotent(domain_target):
    scan = make_scan(domain_target, ("dns",))

    execute_scan(scan.id, lambda name: SuccessfulCollector())
    execute_scan(scan.id, lambda name: SuccessfulCollector())

    scan.refresh_from_db()
    module = scan.modules.get()
    assert scan.state == Scan.State.SUCCEEDED
    assert scan.started_at is not None and scan.finished_at is not None
    assert module.state == ScanModule.State.SUCCEEDED
    assert module.progress == 100
    assert Evidence.objects.filter(scan=scan).count() == 1


@pytest.mark.django_db
def test_engine_isolates_unknown_module_failure(domain_target):
    scan = make_scan(domain_target, ("dns", "not_implemented"))

    execute_scan(
        scan.id,
        lambda name: SuccessfulCollector() if name == "dns" else None,
    )

    scan.refresh_from_db()
    assert scan.state == Scan.State.FAILED
    assert scan.modules.get(module="dns").state == ScanModule.State.SUCCEEDED
    unsupported = scan.modules.get(module="not_implemented")
    assert unsupported.state == ScanModule.State.FAILED
    assert unsupported.safe_error_code == "unsupported_module"


@pytest.mark.django_db
def test_cancellation_is_immediately_terminal(domain_target):
    scan = make_scan(domain_target, ("dns", "tls"))

    assert transition_to_cancelled(scan.id)

    scan.refresh_from_db()
    assert scan.state == Scan.State.CANCELLED
    assert scan.finished_at is not None
    assert set(scan.modules.values_list("state", flat=True)) == {ScanModule.State.CANCELLED}
    assert set(scan.modules.values_list("progress", flat=True)) == {100}


@pytest.mark.django_db
@pytest.mark.parametrize("module", ["x" * 101, "unknown_module"])
def test_scan_create_rejects_invalid_configured_module(user, domain_target, module):
    configuration = ScanConfiguration.objects.create(
        target=domain_target,
        name="invalid modules",
        enabled_modules=[module],
        created_by=user,
    )
    client = APIClient()
    client.force_authenticate(user)

    response = client.post(
        "/api/v1/scans/",
        {"target": str(domain_target.id), "configuration": str(configuration.id)},
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"
