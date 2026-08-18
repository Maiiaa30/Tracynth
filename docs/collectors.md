# Collectors

Every collector exposes metadata and a version, supported target types, a typed
configuration schema, `can_run`, bounded execution with cooperative cancellation,
normalization, and production of evidence-backed entities, relationships, and
findings. Collector code never writes arbitrary database rows.

All results retain collector/version, target, retrieval time, source or query
provenance, confidence, normalization version, safe evidence reference or
redacted excerpt, and retry/error information. A module failure is isolated from
the rest of the scan.

## Common limits

Collectors define connect/read/overall timeouts, maximum bytes, rate and
concurrency limits, retry categories, cache behavior, and cancellation points.
Retries use capped backoff with jitter and do not retry permanent validation,
policy, authentication, or rate-limit failures blindly.

Network collectors share one destination policy. Static HTTP is preferred;
Scrapy runs in a dedicated subprocess/worker, and Playwright is reserved for
selected JavaScript-dependent pages under the same navigation and download
policy.

## Domain modules

The domain workflow covers DNS/mail posture, direct TLS certificates,
certificate-transparency provenance, RDAP, standard endpoints, bounded crawling,
document discovery, and safe extraction. DKIM checks are limited to explicitly
configured selectors. No general directory wordlist probing is performed.

## Identity sources

Public profile definitions are configuration-driven and independently enabled.
Exact username checks distinguish found, unknown identity, not found, blocked,
and unverifiable states. Evidence explains the relationship reason, and only the
operator can confirm or reject identity. Search companion links open generated
queries in the operator's own browser; the application does not scrape search
engines.

Source behavior, published terms, and technical limitations must be reviewed
before enabling a definition in production.
