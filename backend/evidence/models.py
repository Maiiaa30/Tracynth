import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from entities.models import Entity, Relationship
from scans.models import Scan
from targets.models import Target


class Evidence(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scan = models.ForeignKey(
        Scan, null=True, blank=True, related_name="evidence", on_delete=models.SET_NULL
    )
    target = models.ForeignKey(
        Target, null=True, blank=True, related_name="evidence", on_delete=models.SET_NULL
    )
    entity = models.ForeignKey(
        Entity, null=True, blank=True, related_name="evidence", on_delete=models.SET_NULL
    )
    collector_name = models.CharField(max_length=100, db_index=True)
    collector_version = models.CharField(max_length=50)
    source = models.CharField(max_length=2000)
    retrieved_at = models.DateTimeField(db_index=True)
    confidence = models.DecimalField(
        max_digits=4, decimal_places=3, validators=(MinValueValidator(0), MaxValueValidator(1))
    )
    normalization_version = models.CharField(max_length=50)
    safe_excerpt = models.TextField(blank=True, max_length=4000)
    artifact_reference = models.CharField(max_length=255, blank=True)
    content_sha256 = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-retrieved_at",)
        indexes = [
            models.Index(fields=("collector_name", "retrieved_at"), name="evidence_collector_idx")
        ]


class RelationshipEvidence(models.Model):
    relationship = models.ForeignKey(Relationship, on_delete=models.CASCADE)
    evidence = models.ForeignKey(Evidence, on_delete=models.CASCADE)
    rationale = models.CharField(max_length=500, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("relationship", "evidence"), name="relationship_evidence_unique"
            )
        ]
