#!/usr/bin/env python3
"""Check that this specific Celery worker responds to control messages."""

from __future__ import annotations

import os
import socket
import sys

from config.celery import app


def main() -> int:
    destination = os.getenv(
        "CELERY_WORKER_HEALTH_DESTINATION", f"celery@{socket.gethostname()}"
    )
    timeout = float(os.getenv("CELERY_WORKER_HEALTH_TIMEOUT", "5"))
    try:
        replies = app.control.ping(destination=[destination], timeout=timeout)
    except Exception as exc:  # Celery transports expose several backend exceptions.
        print(f"unhealthy: {type(exc).__name__}", file=sys.stderr)
        return 1
    healthy = any(
        destination in reply and reply[destination].get("ok") == "pong" for reply in replies
    )
    if not healthy:
        print(f"unhealthy: worker {destination!r} did not respond", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
