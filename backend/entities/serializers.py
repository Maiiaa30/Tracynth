from rest_framework import serializers

from .models import Entity, Relationship


class EntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Entity
        fields = (
            "id",
            "entity_type",
            "display_value",
            "normalized_value",
            "state",
            "first_seen_at",
            "last_seen_at",
        )
        read_only_fields = ("id", "first_seen_at", "last_seen_at")


class RelationshipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Relationship
        fields = (
            "id",
            "source",
            "target",
            "relationship_type",
            "confidence",
            "state",
            "first_seen_at",
            "last_seen_at",
        )
        read_only_fields = ("id", "first_seen_at", "last_seen_at")

    def validate(self, attrs):
        source = attrs.get("source", getattr(self.instance, "source", None))
        target = attrs.get("target", getattr(self.instance, "target", None))
        if source == target:
            raise serializers.ValidationError("A relationship cannot point to itself.")
        return attrs
