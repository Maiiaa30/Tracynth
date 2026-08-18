from rest_framework import serializers

from .models import Finding


class FindingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Finding
        fields = (
            "id",
            "scan",
            "affected_entity",
            "finding_type",
            "title",
            "severity",
            "confidence",
            "explanation",
            "remediation",
            "status",
            "verification",
            "first_seen_at",
            "last_seen_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
