# Private deployment

## Prerequisites

- A maintained Linux VPS with Docker Engine and the Compose plugin.
- Tailscale installed, authenticated, and healthy on the host.
- A Tailnet DNS name or the host's stable Tailscale address.
- Host firewall rules that reject inbound public traffic independently of Docker.

Tailscale connectivity does not automatically guarantee that a container port is
private. Validate the Docker and host firewall behavior from both a Tailnet
client and a non-Tailnet network.

## Configure

```bash
git clone https://github.com/Maiiaa30/Tracynth.git
cd Tracynth
cp .env.example .env
chmod 600 .env
```

Replace every `change-me` value. Keep `TRACYNTH_BIND_ADDRESS=127.0.0.1`, set
`TRACYNTH_PUBLIC_ORIGIN` to the final Tailnet HTTPS origin, and use the same
host/origin in `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS`.

Generate independent random secret values, for example:

```bash
openssl rand -hex 48
```

Do not paste generated values into tickets, shell history shared with others, or
tracked files.

## Start and initialize

```bash
docker compose config --quiet
docker compose build
docker compose up -d postgres redis
docker compose run --rm backend python manage.py migrate
docker compose run --rm backend python manage.py create_initial_user --username admin
docker compose up -d
docker compose ps
sudo tailscale serve --bg https / http://127.0.0.1:8080
tailscale serve status
```

Tailscale Serve terminates HTTPS and forwards only Tailnet traffic to the
loopback-bound Caddy listener. Open the configured Tailnet HTTPS origin, sign in, and change the initial
password if a temporary one was used. Confirm login, logout, health, scan-task
creation, and artifact authorization before adding real targets.

## Network verification

On the VPS, confirm published listeners and the Tailscale state:

```bash
tailscale status
ss -lntp
docker compose ps
```

From a Tailnet client, confirm HTTPS access. From a non-Tailnet host, confirm the
service is unreachable. Also inspect the VPS provider firewall and host firewall;
the Compose bind address is a safety layer, not the only control.

## Upgrade

Back up first, review release notes and environment changes, then:

```bash
git pull --ff-only
docker compose build --pull
docker compose run --rm backend python manage.py migrate
docker compose up -d --remove-orphans
docker compose ps
```

Never use a forced Git update on a host containing local changes. Roll back with
a tested database/evidence restore and the previously deployed image/source
revision; schema downgrades are not assumed to be safe.

## Worker scaling

Queue concurrency defaults are intentionally conservative. Raise one queue at a
time through the corresponding environment value after measuring memory, CPU,
remote rate limits, database load, and task latency. Browser and file parsers
have higher per-task resource risk and should remain isolated.
