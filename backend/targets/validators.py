from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator, validate_domain_name


def validate_public_domain(value: str) -> None:
    hostname = value.strip().rstrip(".").casefold()
    try:
        ascii_hostname = hostname.encode("idna").decode("ascii")
        validate_domain_name(ascii_hostname)
    except (UnicodeError, ValidationError) as exc:
        raise ValidationError("Enter a valid domain name.", code="invalid_domain") from exc
    if (
        not hostname
        or hostname in {"localhost", "localhost.localdomain"}
        or hostname.endswith((".localhost", ".local"))
    ):
        raise ValidationError("Local domain names are not permitted.", code="non_public_domain")
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        return
    raise ValidationError("An IP address is not a domain target.", code="invalid_domain")


def validate_public_http_url(value: str) -> None:
    """Reject URL forms that can trivially cross the collector trust boundary.

    DNS is intentionally re-resolved and validated by collectors immediately
    before each connection and redirect; request-time DNS checks alone are
    vulnerable to DNS rebinding.
    """

    try:
        parsed = urlsplit(value)
        URLValidator(schemes=("http", "https"))(value)
    except (ValueError, ValidationError) as exc:
        raise ValidationError("Enter a valid HTTP(S) URL.", code="invalid_url") from exc
    if parsed.scheme.casefold() not in {"http", "https"}:
        raise ValidationError("Only HTTP(S) URLs are permitted.", code="invalid_scheme")
    if parsed.username is not None or parsed.password is not None:
        raise ValidationError("URL credentials are not permitted.", code="credentials_forbidden")
    hostname = (parsed.hostname or "").rstrip(".").casefold()
    if (
        not hostname
        or hostname in {"localhost", "localhost.localdomain"}
        or hostname.endswith(".localhost")
    ):
        raise ValidationError(
            "Local destinations are not permitted.", code="non_public_destination"
        )
    compact_hostname = hostname.replace(".", "")
    if compact_hostname.isdigit() or compact_hostname.startswith("0x"):
        raise ValidationError(
            "Ambiguous numeric hosts are not permitted.", code="ambiguous_hostname"
        )
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        try:
            hostname.encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise ValidationError("The hostname is invalid.", code="invalid_hostname") from exc
    else:
        if not address.is_global:
            raise ValidationError(
                "Non-public destinations are not permitted.", code="non_public_destination"
            )


def normalize_target(target_type: str, value: str) -> str:
    cleaned = value.strip()
    if target_type in {"domain", "email", "username"}:
        return cleaned.rstrip(".").casefold() if target_type == "domain" else cleaned.casefold()
    if target_type == "url":
        parsed = urlsplit(cleaned)
        raw_hostname = parsed.hostname or ""
        try:
            address = ipaddress.ip_address(raw_hostname)
        except ValueError:
            hostname = raw_hostname.encode("idna").decode("ascii").casefold()
        else:
            hostname = f"[{address.compressed}]" if address.version == 6 else address.compressed
        port = f":{parsed.port}" if parsed.port else ""
        return f"{parsed.scheme.casefold()}://{hostname}{port}{parsed.path or '/'}" + (
            f"?{parsed.query}" if parsed.query else ""
        )
    return cleaned
