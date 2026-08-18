#!/usr/bin/env python3
"""Reject Compose settings that accidentally make the private stack public."""

from __future__ import annotations

import argparse
import ipaddress
import json
from pathlib import Path
import subprocess
import sys


TAILSCALE_V4 = ipaddress.ip_network("100.64.0.0/10")
TAILSCALE_V6 = ipaddress.ip_network("fd7a:115c:a1e0::/48")
SOCKET_MARKERS = ("/var/run/docker.sock", "//./pipe/docker_engine")


def is_private_bind(value: str | None) -> bool:
    if not value:
        return False
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return address.is_loopback or address in TAILSCALE_V4 or address in TAILSCALE_V6


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compose-file", type=Path)
    parser.add_argument("--proxy-service", default="caddy")
    parser.add_argument("--private-service", action="append")
    args = parser.parse_args()

    command = ["docker", "compose"]
    if args.compose_file:
        command.extend(["--file", str(args.compose_file)])
    command.extend(["config", "--format", "json"])
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        config = json.loads(result.stdout)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"error: could not read Compose configuration: {exc}", file=sys.stderr)
        return 1

    errors: list[str] = []
    services = config.get("services", {})
    networks = config.get("networks", {})
    for name, service in services.items():
        if service.get("privileged"):
            errors.append(f"{name}: privileged containers are forbidden")
        for volume in service.get("volumes", []):
            source = str(volume.get("source", "")).replace("\\", "/").lower()
            if any(marker in source for marker in SOCKET_MARKERS):
                errors.append(f"{name}: mounting the Docker socket is forbidden")

        ports = service.get("ports", [])
        if name != args.proxy_service and ports:
            errors.append(f"{name}: only {args.proxy_service} may publish host ports")
        if name == args.proxy_service:
            for port in ports:
                host_ip = port.get("host_ip")
                if not is_private_bind(host_ip):
                    errors.append(
                        f"{name}: published port {port.get('published')} must bind to a "
                        f"loopback or literal Tailscale address, not {host_ip!r}"
                    )

    for name in args.private_service or ["postgres", "redis"]:
        service = services.get(name)
        if service is None:
            errors.append(f"required private service {name!r} is missing")
            continue
        attached = service.get("networks", {})
        has_external_network = any(
            not networks.get(network, {}).get("internal") for network in attached
        )
        if not attached or has_external_network:
            errors.append(f"{name}: every attached network must be marked internal")

    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    print("Compose security boundary check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
