import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from entities.models import Entity
from evidence.models import Evidence


class Incident(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=250)
    incident_type = models.CharField(max_length=80, db_index=True)
    source = models.CharField(max_length=2000)
    disclosed_at = models.DateTimeField(db_index=True)
    confidence = models.DecimalField(
        max_digits=4, decimal_places=3, validators=(MinValueValidator(0), MaxValueValidator(1))
    )
    summary = models.TextField(blank=True, max_length=4000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-disclosed_at",)


class ExposureMatch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    incident = models.ForeignKey(Incident, related_name="matches", on_delete=models.CASCADE)
    entity = models.ForeignKey(Entity, related_name="exposure_matches", on_delete=models.PROTECT)
    evidence = models.ForeignKey(Evidence, null=True, blank=True, on_delete=models.PROTECT)
    identifier_hash = models.CharField(max_length=64, db_index=True)
    redacted_evidence = models.CharField(max_length=500)
    match_method = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("incident", "entity", "identifier_hash"),
                name="incident_entity_identifier_unique",
            )
        ]
