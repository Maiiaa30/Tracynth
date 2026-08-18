from __future__ import annotations

import ipaddress
import socket
import ssl
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urljoin, urlsplit

import httpcore
import httpx
from httpcore._backends.base import SOCKET_OPTION, NetworkStream
from httpcore._backends.sync import SyncBackend


class NetworkPolicyError(RuntimeError):
    """A safe, non-secret-bearing network policy failure."""


class InvalidDestination(NetworkPolicyError):
    pass


class ResponseLimitExceeded(NetworkPolicyError):
    pass


class CollectionCancelled(NetworkPolicyError):
    pass


class Resolver(Protocol):
    def resolve(self, hostname: str, port: int) -> tuple[str, ...]: ...


class SystemResolver:
    def resolve(self, hostname: str, port: int) -> tuple[str, ...]:
        try:
            answers = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise InvalidDestination("destination_resolution_failed") from exc
        addresses = tuple(dict.fromkeys(str(answer[4][0]) for answer in answers))
        if not addresses:
            raise InvalidDestination("destination_resolution_failed")
        return addresses


def validate_public_address(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
    try:
        address = ipaddress.ip_address(value)
    except ValueError as exc:
        raise InvalidDestination("invalid_resolved_address") from exc
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    if not address.is_global:
        raise InvalidDestination("non_public_destination")
    return address


def resolve_public(resolver: Resolver, hostname: str, port: int) -> tuple[str, ...]:
    addresses = resolver.resolve(hostname, port)
    if not addresses:
        raise InvalidDestination("destination_resolution_failed")
    # Reject the whole DNS answer if any address could pivot into a protected range.
    for address in addresses:
        validate_public_address(address)
    return addresses


def validate_http_url(url: str) -> tuple[str, int]:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise InvalidDestination("invalid_url") from exc
    scheme = parsed.scheme.casefold()
    if scheme not in {"http", "https"}:
        raise InvalidDestination("invalid_scheme")
    if parsed.username is not None or parsed.password is not None:
        raise InvalidDestination("credentials_forbidden")
    hostname = (parsed.hostname or "").rstrip(".").casefold()
    if not hostname or hostname == "localhost" or hostname.endswith(".localhost"):
        raise InvalidDestination("non_public_destination")
    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        compact = hostname.replace(".", "")
        if compact.isdigit() or compact.startswith("0x"):
            raise InvalidDestination("ambiguous_hostname")
        try:
            hostname = hostname.encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise InvalidDestination("invalid_hostname") from exc
    else:
        validate_public_address(str(literal))
    return hostname, port or (443 if scheme == "https" else 80)


class _PinnedNetworkBackend(SyncBackend):
    """Resolve, validate, and pin the address at the actual TCP connection."""

    def __init__(self, resolver: Resolver) -> None:
        self._resolver = resolver

    def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[SOCKET_OPTION] | None = None,
    ) -> NetworkStream:
        addresses = resolve_public(self._resolver, host, port)
        return super().connect_tcp(
            addresses[0],
            port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )

    def connect_unix_socket(
        self,
        path: str,
        timeout: float | None = None,
        socket_options: Iterable[SOCKET_OPTION] | None = None,
    ) -> NetworkStream:
        raise InvalidDestination("unix_sockets_forbidden")


class _PinnedHTTPTransport(httpx.HTTPTransport):
    def __init__(self, resolver: Resolver) -> None:
        super().__init__(verify=True, trust_env=False, retries=0)
        self._pool = httpcore.ConnectionPool(
            ssl_context=ssl.create_default_context(),
            max_connections=4,
            max_keepalive_connections=0,
            network_backend=_PinnedNetworkBackend(resolver),
        )


@dataclass(frozen=True, slots=True)
class HTTPResponse:
    url: str
    status_code: int
    headers: Mapping[str, str]
    body: bytes

    @property
    def text(self) -> str:
        content_type = self.headers.get("content-type", "")
        charset = "utf-8"
        for part in content_type.split(";")[1:]:
            name, _, value = part.strip().partition("=")
            if name.casefold() == "charset" and value:
                charset = value.strip('"')
        try:
            return self.body.decode(charset, errors="replace")
        except LookupError:
            return self.body.decode("utf-8", errors="replace")


class SSRFSafeHTTPClient:
    """Bounded HTTPX client with manual redirect validation and DNS pinning."""

    def __init__(
        self,
        *,
        resolver: Resolver | None = None,
        max_requests: int,
        max_response_bytes: int,
        timeout_seconds: int,
        max_redirects: int,
        cancellation_requested: Callable[[], bool],
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.resolver = resolver or SystemResolver()
        self.max_requests = max_requests
        self.max_response_bytes = max_response_bytes
        self.timeout_seconds = timeout_seconds
        self.max_redirects = max_redirects
        self.cancellation_requested = cancellation_requested
        self.request_count = 0
        self._client = httpx.Client(
            transport=transport or _PinnedHTTPTransport(self.resolver),
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=False,
            trust_env=False,
            headers={"User-Agent": "TracynthPassiveCollector/1.0"},
        )

    def __enter__(self) -> SSRFSafeHTTPClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def get(self, url: str) -> HTTPResponse:
        current = url
        for redirect_number in range(self.max_redirects + 1):
            if self.cancellation_requested():
                raise CollectionCancelled("collection_cancelled")
            if self.request_count >= self.max_requests:
                raise ResponseLimitExceeded("request_limit_exceeded")
            hostname, port = validate_http_url(current)
            # Validate before dispatch; the default transport independently resolves
            # and validates again when it opens the TCP connection.
            resolve_public(self.resolver, hostname, port)
            self.request_count += 1
            with self._client.stream("GET", current) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        return HTTPResponse(
                            str(response.url), response.status_code, dict(response.headers), b""
                        )
                    if redirect_number >= self.max_redirects:
                        raise ResponseLimitExceeded("redirect_limit_exceeded")
                    current = urljoin(str(response.url), location)
                    validate_http_url(current)
                    continue
                declared_size = response.headers.get("content-length")
                if declared_size:
                    try:
                        if int(declared_size) > self.max_response_bytes:
                            raise ResponseLimitExceeded("response_too_large")
                    except ValueError:
                        pass
                chunks: list[bytes] = []
                size = 0
                for chunk in response.iter_bytes():
                    if self.cancellation_requested():
                        raise CollectionCancelled("collection_cancelled")
                    size += len(chunk)
                    if size > self.max_response_bytes:
                        raise ResponseLimitExceeded("response_too_large")
                    chunks.append(chunk)
                return HTTPResponse(
                    str(response.url),
                    response.status_code,
                    dict(response.headers),
                    b"".join(chunks),
                )
        raise ResponseLimitExceeded("redirect_limit_exceeded")
