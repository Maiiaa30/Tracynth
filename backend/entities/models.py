import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Entity(models.Model):
    class State(models.TextChoices):
        ACTIVE = "active", "Active"
        DISMISSED = "dismissed", "Dismissed"
        MERGED = "merged", "Merged"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity_type = models.CharField(max_length=50, db_index=True)
    display_value = models.CharField(max_length=1000)
    normalized_value = models.CharField(max_length=1000)
    state = models.CharField(
        max_length=20, choices=State.choices, default=State.ACTIVE, db_index=True
    )
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("entity_type", "normalized_value")
        constraints = [
            models.UniqueConstraint(
                fields=("entity_type", "normalized_value"), name="entity_type_value_unique"
            )
        ]
        indexes = [
            models.Index(fields=("entity_type", "normalized_value"), name="entity_type_value_idx")
        ]


class Relationship(models.Model):
    class State(models.TextChoices):
        UNREVIEWED = "unreviewed", "Unreviewed"
        CONFIRMED = "confirmed", "Confirmed"
        DISMISSED = "dismissed", "Dismissed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey(
        Entity, related_name="outgoing_relationships", on_delete=models.CASCADE
    )
    target = models.ForeignKey(
        Entity, related_name="incoming_relationships", on_delete=models.CASCADE
    )
    relationship_type = models.CharField(max_length=80)
    confidence = models.DecimalField(
        max_digits=4, decimal_places=3, validators=(MinValueValidator(0), MaxValueValidator(1))
    )
    state = models.CharField(
        max_length=20, choices=State.choices, default=State.UNREVIEWED, db_index=True
    )
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-last_seen_at",)
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(source=models.F("target")), name="relationship_not_self"
            ),
            models.UniqueConstraint(
                fields=("source", "target", "relationship_type"), name="relationship_edge_unique"
            ),
        ]
        indexes = [
            models.Index(fields=("source", "relationship_type"), name="relationship_source_idx"),
            models.Index(fields=("target", "relationship_type"), name="relationship_target_idx"),
        ]
