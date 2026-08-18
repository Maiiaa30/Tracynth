import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .validators import normalize_target, validate_public_domain, validate_public_http_url


class Target(models.Model):
    class Type(models.TextChoices):
        DOMAIN = "domain", "Domain"
        URL = "url", "URL"
        IDENTITY = "identity", "Identity"
        EMAIL = "email", "Email"
        USERNAME = "username", "Username"
        FILE = "file", "File"

    class State(models.TextChoices):
        ACTIVE = "active", "Active"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target_type = models.CharField(max_length=20, choices=Type.choices, db_index=True)
    display_value = models.CharField(max_length=1000)
    normalized_value = models.CharField(max_length=1000, blank=True)
    state = models.CharField(
        max_length=20, choices=State.choices, default=State.ACTIVE, db_index=True
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("target_type", "normalized_value"), name="target_type_value_unique"
            )
        ]
        indexes = [models.Index(fields=("target_type", "state"), name="target_type_state_idx")]

    def clean(self):
        super().clean()
        if self.target_type == self.Type.URL:
            validate_public_http_url(self.display_value)
        elif self.target_type == self.Type.DOMAIN:
            validate_public_domain(self.display_value)
        if not self.display_value.strip():
            raise ValidationError({"display_value": "This value may not be blank."})
        self.normalized_value = normalize_target(self.target_type, self.display_value)

    def save(self, *args, **kwargs):
        if self.target_type == self.Type.URL:
            validate_public_http_url(self.display_value)
        elif self.target_type == self.Type.DOMAIN:
            validate_public_domain(self.display_value)
        self.normalized_value = normalize_target(self.target_type, self.display_value)
        super().save(*args, **kwargs)


class ScanConfiguration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    target = models.ForeignKey(Target, related_name="configurations", on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    enabled_modules = models.JSONField(default=list)
    collector_settings = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(fields=("target", "name"), name="target_config_name_unique")
        ]
