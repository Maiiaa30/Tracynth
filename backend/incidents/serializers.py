from rest_framework import serializers

from .models import Incident


class IncidentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Incident
        fields = (
            "id",
            "title",
            "incident_type",
            "source",
            "disclosed_at",
            "confidence",
            "summary",
            "created_at",
        )
        read_only_fields = fields
