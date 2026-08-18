from rest_framework import serializers

from collectors import COLLECTOR_FACTORIES

from .models import MonitoringSchedule, Scan, ScanModule


class ScanModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanModule
        fields = (
            "id",
            "module",
            "attempt",
            "state",
            "progress",
            "safe_error_code",
            "started_at",
            "finished_at",
        )
        read_only_fields = fields


class ScanSerializer(serializers.ModelSerializer):
    modules = ScanModuleSerializer(many=True, read_only=True)

    class Meta:
        model = Scan
        fields = (
            "id",
            "target",
            "configuration",
            "scope_snapshot",
            "state",
            "cancellation_requested",
            "created_at",
            "started_at",
            "finished_at",
            "modules",
        )
        read_only_fields = (
            "id",
            "scope_snapshot",
            "state",
            "cancellation_requested",
            "created_at",
            "started_at",
            "finished_at",
            "modules",
        )

    def validate(self, attrs):
        configuration = attrs.get("configuration")
        target = attrs.get("target")
        if configuration and configuration.target_id != target.id:
            raise serializers.ValidationError(
                {"configuration": "Configuration must belong to the selected target."}
            )
        if configuration:
            modules = configuration.enabled_modules
            if (
                not isinstance(modules, list)
                or not all(isinstance(module, str) and module for module in modules)
                or len(modules) > 50
            ):
                raise serializers.ValidationError(
                    {"configuration": "Enabled modules must be a list of names."}
                )
            invalid = [
                module
                for module in modules
                if len(module) > 100 or module.casefold() not in COLLECTOR_FACTORIES
            ]
            if invalid:
                raise serializers.ValidationError(
                    {"configuration": "Configuration contains an unsupported module."}
                )
        return attrs

    def create(self, validated_data):
        configuration = validated_data.get("configuration")
        validated_data["scope_snapshot"] = {
            "target_id": str(validated_data["target"].id),
            "target_type": validated_data["target"].target_type,
            "normalized_value": validated_data["target"].normalized_value,
            "enabled_modules": (
                list(dict.fromkeys(configuration.enabled_modules)) if configuration else []
            ),
            "collector_settings": dict(configuration.collector_settings) if configuration else {},
        }
        return super().create(validated_data)


class MonitoringScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonitoringSchedule
        fields = (
            "id",
            "target",
            "configuration",
            "schedule",
            "enabled",
            "next_run_at",
            "created_at",
        )
        read_only_fields = fields
