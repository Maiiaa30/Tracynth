#!/usr/bin/env python3
"""Small dependency-free health probe for application containers."""

from __future__ import annotations

import argparse
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request


def check_url(url: str, timeout: float) -> None:
    if urllib.parse.urlsplit(url).scheme not in {"http", "https"}:
        raise RuntimeError("URL probe permits only HTTP(S)")
    request = urllib.request.Request(url, headers={"User-Agent": "tracynth-health/1"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=timeout) as response:
        if not 200 <= response.status < 400:
            raise RuntimeError(f"unexpected HTTP status {response.status}")
        response.read(1024)


def check_tcp(host: str, port: int, timeout: float) -> None:
    with socket.create_connection((host, port), timeout=timeout):
        pass


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--timeout", type=float, default=3.0)
    subparsers = result.add_subparsers(dest="probe", required=True)
    url_parser = subparsers.add_parser("url")
    url_parser.add_argument("url")
    tcp_parser = subparsers.add_parser("tcp")
    tcp_parser.add_argument("host")
    tcp_parser.add_argument("port", type=int)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.probe == "url":
            check_url(args.url, args.timeout)
        else:
            check_tcp(args.host, args.port, args.timeout)
    except (OSError, RuntimeError, urllib.error.URLError) as exc:
        print(f"unhealthy: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
