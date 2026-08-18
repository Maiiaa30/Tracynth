from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache


@dataclass(frozen=True)
class BackoffState:
    blocked: bool
    retry_after: int = 0


def _digest(scope: str) -> str:
    return hashlib.sha256(scope.encode()).hexdigest()


def _scopes(username: str, remote_addr: str) -> tuple[tuple[str, int], ...]:
    account = _digest(f"account\0{username.casefold().strip()}\0{remote_addr}")
    client = _digest(f"client\0{remote_addr}")
    return (
        (account, settings.LOGIN_BACKOFF_THRESHOLD),
        (client, settings.LOGIN_GLOBAL_BACKOFF_THRESHOLD),
    )


def _increment(key: str, timeout: int) -> int:
    if cache.add(key, 1, timeout=timeout):
        return 1
    try:
        return int(cache.incr(key))
    except ValueError:
        cache.set(key, 1, timeout=timeout)
        return 1


def state(username: str, remote_addr: str) -> BackoffState:
    blocked_until = max(
        (
            float(cache.get(f"login-blocked:{scope}") or 0)
            for scope, _ in _scopes(username, remote_addr)
        ),
        default=0,
    )
    retry_after = max(0, int(blocked_until - time.time() + 0.999))
    return BackoffState(bool(retry_after), retry_after)


def record_failure(username: str, remote_addr: str) -> BackoffState:
    delay = 0
    timeout = settings.LOGIN_BACKOFF_MAX_SECONDS * 2
    for scope, threshold in _scopes(username, remote_addr):
        failures = _increment(f"login-failures:{scope}", timeout)
        if failures >= threshold:
            exponent = failures - threshold
            scope_delay = min(
                settings.LOGIN_BACKOFF_MAX_SECONDS,
                settings.LOGIN_BACKOFF_BASE_SECONDS * 2**exponent,
            )
            delay = max(delay, scope_delay)
            cache.set(f"login-blocked:{scope}", time.time() + scope_delay, timeout=timeout)
    return BackoffState(bool(delay), delay)


def clear(username: str, remote_addr: str) -> None:
    account_scope = _scopes(username, remote_addr)[0][0]
    cache.delete_many((f"login-failures:{account_scope}", f"login-blocked:{account_scope}"))
