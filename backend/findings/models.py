import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from entities.models import Entity
from evidence.models import Evidence
from scans.models import Scan


class Finding(models.Model):
    class Severity(models.TextChoices):
        INFO = "info", "Info"
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        REMEDIATED = "remediated", "Remediated"
        DISMISSED = "dismissed", "Dismissed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scan = models.ForeignKey(Scan, null=True, blank=True, on_delete=models.SET_NULL)
    affected_entity = models.ForeignKey(Entity, related_name="findings", on_delete=models.PROTECT)
    finding_type = models.CharField(max_length=100, db_index=True)
    title = models.CharField(max_length=250)
    severity = models.CharField(max_length=20, choices=Severity.choices, db_index=True)
    confidence = models.DecimalField(
        max_digits=4, decimal_places=3, validators=(MinValueValidator(0), MaxValueValidator(1))
    )
    explanation = models.TextField()
    remediation = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True
    )
    verification = models.JSONField(default=dict, blank=True)
    first_seen_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-last_seen_at",)
        indexes = [models.Index(fields=("severity", "status"), name="finding_severity_status_idx")]


class FindingEvidence(models.Model):
    finding = models.ForeignKey(Finding, related_name="evidence_links", on_delete=models.CASCADE)
    evidence = models.ForeignKey(Evidence, on_delete=models.PROTECT)
    rationale = models.CharField(max_length=500, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("finding", "evidence"), name="finding_evidence_unique")
        ]
