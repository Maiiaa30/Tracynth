from rest_framework import serializers

from .models import FileMetadataEntry, StoredFile


class FileMetadataEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = FileMetadataEntry
        fields = (
            "id",
            "key",
            "value_type",
            "value",
            "extractor_name",
            "extractor_version",
            "source_location",
            "created_at",
        )
        read_only_fields = fields


class StoredFileSerializer(serializers.ModelSerializer):
    metadata_entries = FileMetadataEntrySerializer(many=True, read_only=True)

    class Meta:
        model = StoredFile
        fields = (
            "id",
            "display_name",
            "sha256",
            "detected_mime_type",
            "size_bytes",
            "source",
            "retention_until",
            "analysis_state",
            "created_at",
            "metadata_entries",
        )
        read_only_fields = fields
