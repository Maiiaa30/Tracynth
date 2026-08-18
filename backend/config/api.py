from __future__ import annotations

import logging

from django.http import JsonResponse
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


class StandardPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


def stable_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled API exception", exc_info=exc)
        return Response(
            {
                "error": {
                    "code": "internal_error",
                    "message": "The request could not be completed.",
                    "fields": {},
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    fields = response.data if isinstance(response.data, dict) else {}
    detail = fields.pop("detail", None) if isinstance(fields, dict) else None
    if isinstance(detail, list):
        detail = " ".join(str(item) for item in detail)
    if not detail:
        detail = {
            status.HTTP_400_BAD_REQUEST: "The submitted data is invalid.",
            status.HTTP_401_UNAUTHORIZED: "Authentication is required.",
            status.HTTP_403_FORBIDDEN: "You do not have permission to perform this action.",
            status.HTTP_404_NOT_FOUND: "The requested resource was not found.",
            status.HTTP_405_METHOD_NOT_ALLOWED: "This method is not allowed.",
            status.HTTP_429_TOO_MANY_REQUESTS: "Too many requests.",
        }.get(response.status_code, "The request could not be completed.")

    code = getattr(exc, "default_code", None)
    if code == "invalid":
        code = "validation_error"
    if not code:
        code = {
            400: "validation_error",
            401: "not_authenticated",
            403: "permission_denied",
            404: "not_found",
            405: "method_not_allowed",
            429: "throttled",
        }.get(response.status_code, "request_error")
    response.data = {"error": {"code": str(code), "message": str(detail), "fields": fields}}
    return response


def api_not_found(request, path=""):
    return JsonResponse(
        {
            "error": {
                "code": "not_found",
                "message": "The requested API resource was not found.",
                "fields": {},
            }
        },
        status=404,
    )
