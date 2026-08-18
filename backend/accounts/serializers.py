from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import ApplicationSetting, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name", "is_staff")
        read_only_fields = fields


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, trim_whitespace=True)
    password = serializers.CharField(max_length=1024, trim_whitespace=False, write_only=True)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        max_length=1024, trim_whitespace=False, write_only=True
    )
    new_password = serializers.CharField(max_length=1024, trim_whitespace=False, write_only=True)

    def validate_new_password(self, value):
        validate_password(value, self.context["request"].user)
        return value


class ApplicationSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationSetting
        fields = ("key", "value", "description", "updated_at")
        read_only_fields = ("updated_at",)

    def validate_key(self, value):
        if any(
            token in value.casefold() for token in ("secret", "password", "token", "credential")
        ):
            raise serializers.ValidationError(
                "Secret-like settings must be supplied by the runtime environment."
            )
        return value

    def validate_value(self, value):
        forbidden = ("secret", "password", "token", "credential", "api_key")

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
            raise serializers.ValidationError(
                "Secret-like settings must be supplied by the runtime environment."
            )
        return value
