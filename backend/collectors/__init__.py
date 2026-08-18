from __future__ import annotations

from collections.abc import Callable

from .base.contract import Collector
from .dns import DNSCollector
from .tls import TLSCertificateCollector
from .web import WebStandardEndpointsCollector

CollectorFactory = Callable[[], Collector]

COLLECTOR_FACTORIES: dict[str, CollectorFactory] = {
    "dns": DNSCollector,
    "mail_posture": DNSCollector,
    "tls": TLSCertificateCollector,
    "certificates": TLSCertificateCollector,
    "web": WebStandardEndpointsCollector,
    "standard_endpoints": WebStandardEndpointsCollector,
}


def get_collector(module: str) -> Collector | None:
    factory = COLLECTOR_FACTORIES.get(module.casefold())
    return factory() if factory else None


__all__ = [
    "DNSCollector",
    "TLSCertificateCollector",
    "WebStandardEndpointsCollector",
    "get_collector",
]
