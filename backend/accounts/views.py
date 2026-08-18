from __future__ import annotations

import hashlib
import logging

from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.core.cache import cache
from django.db import connection, transaction
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.http import require_GET
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import backoff
from .models import ApplicationSetting, AuditEvent, User
from .serializers import (
    ApplicationSettingSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    UserSerializer,
)

logger = logging.getLogger(__name__)


def _fingerprint(request) -> str:
    address = request.META.get("REMOTE_ADDR", "")
    agent = request.META.get("HTTP_USER_AGENT", "")[:250]
    return hashlib.sha256(f"{address}\0{agent}".encode()).hexdigest()


def _error(code: str, message: str, *, fields=None, status_code=400, headers=None):
    response = Response(
        {"error": {"code": code, "message": message, "fields": fields or {}}},
        status=status_code,
    )
    for key, value in (headers or {}).items():
        response[key] = value
    return response


@require_GET
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        cache.set("health-check", "ok", timeout=5)
        if cache.get("health-check") != "ok":
            raise RuntimeError("Cache health check failed")
    except Exception:
        logger.warning("Health dependency check failed", exc_info=True)
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


@ensure_csrf_cookie
@require_GET
def csrf(request):
    get_token(request)
    return JsonResponse({"csrf": "cookie"})


def csrf_failure(request, reason=""):
    return JsonResponse(
        {"error": {"code": "csrf_failed", "message": "CSRF verification failed.", "fields": {}}},
        status=403,
    )


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    authentication_classes = ()
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return _error(
                "validation_error", "The submitted data is invalid.", fields=serializer.errors
            )
        username = serializer.validated_data["username"]
        remote_addr = request.META.get("REMOTE_ADDR", "")
        current = backoff.state(username, remote_addr)
        if current.blocked:
            return _error(
                "login_backoff",
                "Login is temporarily delayed after repeated failures.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                fields={"retry_after": current.retry_after},
                headers={"Retry-After": str(current.retry_after)},
            )

        user = authenticate(
            request, username=username, password=serializer.validated_data["password"]
        )
        if user is None or not user.is_active:
            delayed = backoff.record_failure(username, remote_addr)
            fingerprint = _fingerprint(request)
            if cache.add(f"login-audit:{fingerprint}", "1", timeout=60):
                AuditEvent.objects.create(
                    event_type="auth.login",
                    outcome="failure",
                    request_fingerprint=fingerprint,
                )
            headers = {"Retry-After": str(delayed.retry_after)} if delayed.blocked else None
            return _error(
                "invalid_credentials",
                "The username or password is invalid.",
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers=headers,
            )

        backoff.clear(username, remote_addr)
        login(request, user)
        request.session["auth_session_version"] = user.session_version
        AuditEvent.objects.create(
            actor=user,
            event_type="auth.login",
            request_fingerprint=_fingerprint(request),
        )
        return Response({"user": UserSerializer(user).data})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        actor = request.user
        logout(request)
        AuditEvent.objects.create(
            actor=actor, event_type="auth.logout", request_fingerprint=_fingerprint(request)
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class LogoutAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        with transaction.atomic():
            actor = User.objects.select_for_update().get(pk=request.user.pk)
            actor.session_version += 1
            actor.save(update_fields=("session_version",))
            AuditEvent.objects.create(
                actor=actor, event_type="auth.logout_all", request_fingerprint=_fingerprint(request)
            )
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return _error(
                "validation_error", "The submitted data is invalid.", fields=serializer.errors
            )
        if not request.user.check_password(serializer.validated_data["current_password"]):
            return _error("invalid_password", "The current password is invalid.", status_code=400)
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=request.user.pk)
            user.set_password(serializer.validated_data["new_password"])
            user.session_version += 1
            user.save(update_fields=("password", "session_version"))
            AuditEvent.objects.create(
                actor=user,
                event_type="auth.password_change",
                request_fingerprint=_fingerprint(request),
            )
        update_session_auth_hash(request, user)
        request.session["auth_session_version"] = user.session_version
        return Response({"user": UserSerializer(user).data})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"user": UserSerializer(request.user).data})


class ApplicationSettingViewSet(viewsets.ModelViewSet):
    queryset = ApplicationSetting.objects.all()
    serializer_class = ApplicationSettingSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "key"

    def perform_create(self, serializer):
        serializer.save(updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
