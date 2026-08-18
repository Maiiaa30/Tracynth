import uuid

from django.conf import settings
from django.db import models


class StoredFile(models.Model):
    class Source(models.TextChoices):
        UPLOAD = "upload", "Upload"
        COLLECTOR = "collector", "Collector"
        DERIVED = "derived", "Derived"

    class State(models.TextChoices):
        PENDING = "pending", "Pending"
        ANALYZING = "analyzing", "Analyzing"
        COMPLETE = "complete", "Complete"
        FAILED = "failed", "Failed"
        QUARANTINED = "quarantined", "Quarantined"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    storage_key = models.CharField(max_length=255, unique=True, editable=False)
    display_name = models.CharField(max_length=255)
    sha256 = models.CharField(max_length=64, unique=True)
    detected_mime_type = models.CharField(max_length=255)
    size_bytes = models.PositiveBigIntegerField()
    source = models.CharField(max_length=20, choices=Source.choices)
    retention_until = models.DateTimeField(null=True, blank=True, db_index=True)
    analysis_state = models.CharField(
        max_length=20, choices=State.choices, default=State.PENDING, db_index=True
    )
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def save(self, *args, **kwargs):
        if not self.storage_key:
            self.storage_key = f"objects/{self.id.hex[:2]}/{self.id.hex}"
        super().save(*args, **kwargs)


class FileMetadataEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stored_file = models.ForeignKey(
        StoredFile, related_name="metadata_entries", on_delete=models.CASCADE
    )
    key = models.CharField(max_length=200)
    value_type = models.CharField(max_length=40)
    value = models.JSONField()
    extractor_name = models.CharField(max_length=100)
    extractor_version = models.CharField(max_length=50)
    source_location = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("stored_file", "key", "extractor_name", "source_location"),
                name="file_metadata_provenance_unique",
            )
        ]


class SanitizationRelationship(models.Model):
    original = models.ForeignKey(
        StoredFile, related_name="sanitized_derivatives", on_delete=models.PROTECT
    )
    derived = models.OneToOneField(
        StoredFile, related_name="sanitized_from", on_delete=models.PROTECT
    )
    sanitizer_name = models.CharField(max_length=100)
    sanitizer_version = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(original=models.F("derived")), name="sanitization_not_self"
            )
        ]
