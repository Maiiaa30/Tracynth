import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from targets.models import ScanConfiguration, Target


class Scan(models.Model):
    class State(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target = models.ForeignKey(Target, related_name="scans", on_delete=models.PROTECT)
    configuration = models.ForeignKey(ScanConfiguration, null=True, on_delete=models.SET_NULL)
    scope_snapshot = models.JSONField(default=dict)
    state = models.CharField(
        max_length=20, choices=State.choices, default=State.QUEUED, db_index=True
    )
    cancellation_requested = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("state", "created_at"), name="scan_state_created_idx")]


class ScanModule(models.Model):
    class State(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scan = models.ForeignKey(Scan, related_name="modules", on_delete=models.CASCADE)
    module = models.CharField(max_length=100)
    attempt = models.PositiveSmallIntegerField(default=1)
    state = models.CharField(
        max_length=20, choices=State.choices, default=State.PENDING, db_index=True
    )
    progress = models.PositiveSmallIntegerField(
        default=0, validators=(MinValueValidator(0), MaxValueValidator(100))
    )
    safe_error_code = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("module", "attempt")
        constraints = [
            models.UniqueConstraint(
                fields=("scan", "module", "attempt"), name="scan_module_attempt_unique"
            )
        ]
        indexes = [models.Index(fields=("state", "created_at"), name="module_state_created_idx")]


class MonitoringSchedule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target = models.ForeignKey(Target, on_delete=models.CASCADE)
    configuration = models.ForeignKey(ScanConfiguration, on_delete=models.CASCADE)
    schedule = models.CharField(max_length=100, help_text="Server-validated scheduler expression")
    enabled = models.BooleanField(default=True)
    next_run_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
