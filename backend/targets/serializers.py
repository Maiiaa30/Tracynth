from rest_framework import serializers

from .models import ScanConfiguration, Target
from .validators import normalize_target, validate_public_domain, validate_public_http_url


class TargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Target
        fields = (
            "id",
            "target_type",
            "display_value",
            "normalized_value",
            "state",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "normalized_value", "created_at", "updated_at")

    def validate(self, attrs):
        target_type = attrs.get("target_type", getattr(self.instance, "target_type", None))
        value = attrs.get("display_value", getattr(self.instance, "display_value", ""))
        if target_type == Target.Type.URL:
            validate_public_http_url(value)
        elif target_type == Target.Type.DOMAIN:
            validate_public_domain(value)
        attrs["normalized_value"] = normalize_target(target_type, value)
        return attrs


class ScanConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanConfiguration
        fields = (
            "id",
            "target",
            "name",
            "enabled_modules",
            "collector_settings",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_enabled_modules(self, value):
        if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
            raise serializers.ValidationError("Expected a list of non-empty module names.")
        if len(value) > 50:
            raise serializers.ValidationError("At most 50 modules may be enabled.")
        return list(dict.fromkeys(value))

    def validate_collector_settings(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Expected an object.")
        forbidden = ("password", "secret", "token", "credential", "api_key")

        def contains_secret_key(item):
            if isinstance(item, dict):
                return any(
                    any(token in str(key).casefold() for token in forbidden)
                    or contains_secret_key(child)
                    for key, child in item.items()
                )
            if isinstance(item, list):
                return any(contains_secret_key(child) for child in item)
            return False

        if contains_secret_key(value):
            raise serializers.ValidationError("Secrets may not be stored in scan configuration.")
        return value
