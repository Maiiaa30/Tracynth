# Tracynth

Tracynth is a private, single-operator exposure-intelligence application for
evidence-backed domain investigations, identity cases, and local file analysis.
It is designed to run on a private VPS reached through Tailscale and protected
again by application login.

The project is under active initial development. Current implementation status
and verified workflows are documented alongside each completed phase; features
are not represented as available until their API, interface, and tests exist.

## Safety scope

Tracynth performs passive, bounded collection of public information and analyzes
operator-supplied files. It does not test credentials, crack passwords, bypass
access controls or CAPTCHAs, download credential dumps, crawl criminal forums,
perform facial recognition, or actively exploit systems. Username similarity is
evidence for review, never proof of identity.

Only process targets and data that you are authorized to investigate. Remote
content and uploaded files are treated as untrusted. Network collectors block
private and special-use destinations by default and apply time, byte, redirect,
rate, depth, and concurrency limits.

## Architecture

- Django 5.2 and Django REST Framework with server-side session authentication
- PostgreSQL for normalized entities, provenance, graph relationships, and search
- Redis and isolated Celery queues for collection, crawling, browser, and file work
- React, strict TypeScript, Vite, TanStack Query, and Cytoscape.js
- Caddy and Docker Compose for one-origin, Tailscale-only deployment

See [Architecture](docs/architecture.md) and [Data model](docs/data-model.md).

## Development setup

Requirements: Python 3.13, Node.js 24, npm 11, and Docker with Compose.

```bash
cp .env.example .env
# Replace every change-me value and set the Tailscale hostname/address.
python -m pip install -e "./backend[dev]"
cd frontend && npm ci && cd ..
python backend/manage.py migrate
python backend/manage.py create_initial_user
```

Run the backend and frontend development servers using the commands documented
in their directories, or start the complete stack:

```bash
docker compose up --build
```

The default Compose bind is loopback port 8080. Production uses Tailscale Serve
to terminate Tailnet HTTPS and forward to that listener. Never bind the service
to all interfaces on a publicly reachable host.

## Quality commands

```bash
make lint
make format-check
make typecheck
make test
make compose-check
make build
```

Equivalent commands are listed in `Makefile` for environments without Make.

## License

Licensed under the MIT License. See [LICENSE](LICENSE).
