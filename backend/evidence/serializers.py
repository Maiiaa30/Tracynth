from rest_framework import serializers

from .models import Evidence


class EvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Evidence
        fields = (
            "id",
            "scan",
            "target",
            "entity",
            "collector_name",
            "collector_version",
            "source",
            "retrieved_at",
            "confidence",
            "normalization_version",
            "safe_excerpt",
            "artifact_reference",
            "content_sha256",
            "created_at",
        )
        read_only_fields = fields
