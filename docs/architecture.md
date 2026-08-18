# Architecture

Tracynth is a modular monolith with a Django REST API, a React single-page
application, PostgreSQL persistence, Redis-backed task coordination, and Celery
workers. Caddy exposes one authenticated origin. PostgreSQL, Redis, worker
services, and evidence storage are not published to the host network.

## Runtime topology

```text
Tailscale client
      |
      v
Caddy :443
  |-- /api/, /admin/, /health/ -> Django/Gunicorn
  `-- all other paths           -> static React application

Django -> PostgreSQL
       -> Redis -> general worker
                -> crawler worker
                -> browser worker
                -> file worker
                -> scheduler
```

The API and browser application share an origin so Django session cookies and
CSRF protection work without cross-origin credentials. Authentication is
required everywhere except a non-sensitive liveness/readiness endpoint.

## Module boundaries

- `accounts`: single-user authentication, session lifecycle, lockout, and audit.
- `targets`: domain and identity targets plus scan configuration.
- `scans`: orchestration, module state, cancellation, retries, and snapshots.
- `entities`: normalized identifiers and evidence-backed relationships.
- `evidence`: immutable provenance records and controlled stored artifacts.
- `findings`: exposure observations, remediation, status, and verification.
- `incidents`: public incident metadata and authorized exact-match imports.
- `filelab`: bounded local extraction, indicator discovery, and sanitization.
- `collectors`: typed, independently testable passive data acquisition adapters.

Collectors return typed normalized results. They do not write arbitrary model
instances. Application services validate and persist collector output in one
transactional boundary and retain collector/version/source provenance.

## Stable HTTP contract

All JSON APIs live below `/api/v1/`. Collection endpoints return paginated
objects shaped as `{count, next, previous, results}`. Errors use:

```json
{
  "error": {
    "code": "stable_machine_code",
    "message": "Safe human-readable explanation",
    "fields": {}
  }
}
```

The SPA obtains a CSRF cookie before login and sends `X-CSRFToken` on unsafe
requests. It polls scan detail for progress; no WebSocket dependency is used.

Core routes are `/api/v1/auth/`, `/targets/`, `/scan-configurations/`, `/scans/`, `/entities/`,
`/relationships/`, `/evidence/`, `/findings/`, `/files/`, `/identities/`,
`/incidents/`, `/monitoring/`, `/alerts/`, `/reports/`, and `/settings/`.

## Task and queue contract

Scan modules are idempotent for a `(scan, module, attempt)` key. The API creates
task state before enqueueing work. Workers report bounded progress and terminal
state through the scan service. Cancellation is cooperative and checked before
network access, between result batches, and before persistence.

Queues are separated by trust and resource profile:

- `general`: orchestration, normalization, correlation, alerts, and reports.
- `crawler`: Scrapy subprocesses with strict crawl budgets.
- `browser`: Playwright navigation with equivalent SSRF and download policy.
- `file`: parsers and sanitizers under file, time, and memory limits.

Only JSON task serialization is permitted. Tasks receive database identifiers,
not secrets or raw imported records.

## Network and file trust boundaries

Operator-supplied network destinations are untrusted. Web collectors allow only
HTTP(S), reject credentials and ambiguous hosts, resolve and validate every hop,
block non-public address classes by default, and enforce redirect, byte, time,
rate, and concurrency limits. Any internal-range exception is server-side
configuration and is unavailable in ordinary API input.

Uploads are stored under generated identifiers outside the served static tree.
Filenames are display metadata only. Archive members are never joined directly
to storage paths. Extractors enforce expanded-size, entry-count, recursion,
compression-ratio, CPU, and wall-clock budgets and never execute active content.

## Data contract

Entities hold typed normalized values. Relationships have source and target
entities, a relationship type, confidence, state, timestamps, and evidence
provenance. Findings reference affected entities and evidence rather than
copying mutable source material. Evidence includes collector name/version,
retrieval time, source, target, confidence, normalization version, and a safe
excerpt or controlled artifact reference.

PostgreSQL provides transactional storage, full-text search, and trigram fuzzy
matching. Graph APIs always paginate and apply a server-side node/edge limit.

## Security posture

There is no public registration. An initial operator account is created with a
management command. Django server-side sessions, Argon2 password hashing,
production secure cookies, CSRF validation, login backoff, and logout-all are
mandatory. Caddy adds transport and browser security headers; Django enforces
authorization again at every sensitive route and artifact access point.

Tailscale limits network reachability while application authentication protects
against unauthorized access from a permitted device. Neither layer replaces the
other.
