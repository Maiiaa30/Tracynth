# Operations

## Routine checks

```bash
docker compose ps
docker compose logs --since=30m backend worker crawler-worker browser-worker file-worker scheduler
docker compose exec backend python manage.py check --deploy
```

Monitor database and evidence-volume growth, queue depth, task retry rate,
collector error categories, worker restarts, browser/file-worker memory, report
generation latency, certificate expiry, backup completion, and restore drills.
Logs should contain internal record IDs and safe error categories, not submitted
identifiers or evidence contents.

## Account recovery

Use the account management command from an authenticated VPS shell. Do not expose
a browser password-reset endpoint or email a password. After recovery, invalidate
existing sessions and review audit events.

```bash
docker compose run --rm backend python manage.py reset_operator_password
docker compose run --rm backend python manage.py logout_all_sessions
```

Exact command options are shown with `--help` and may require the operator
username. Never pass a password directly as a command-line argument.

## Task response

For a retry storm, pause new schedules, inspect the failing module and remote
status, then reduce concurrency or disable that source. Do not repeatedly retry
rate-limited or blocked sources. Cancellation is cooperative; recycle only the
specific queue worker after its task soft limit and grace period have elapsed.

For low disk space, pause scan creation and file ingestion before applying the
documented retention job. Never delete database or evidence-volume paths by hand.
Verify that retained evidence is not referenced before removal.

## Data retention

Configure separate retention for pages, raw evidence, screenshots, files,
reports, completed task metadata, and authorized-import staging. A retention run
must retain audit/provenance records needed to explain surviving findings while
removing expired artifacts through the application service.

## Troubleshooting

- `502` from Caddy: check backend/frontend health and internal DNS names.
- CSRF rejection: verify exact HTTPS origin, trusted origins, proxy headers, and
  that the SPA first obtained the CSRF cookie.
- Tasks remain queued: inspect Redis health and the worker subscribed to the
  module's named queue.
- PostgreSQL connection failure: confirm the unescaped database values and that
  the database is healthy on the internal network.
- Collection blocked: review the normalized destination, resolved IPs, redirect
  chain, and internal allowlist; do not weaken SSRF policy globally as a shortcut.
