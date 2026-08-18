# syntax=docker/dockerfile:1.7

FROM node:24-alpine AS build

ENV NODE_ENV=development
WORKDIR /build

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./
RUN npm run build

FROM caddy:2.10-alpine AS runtime

RUN addgroup -S -g 10001 tracynth \
    && adduser -S -D -H -u 10001 -G tracynth tracynth \
    && setcap -r /usr/bin/caddy

COPY --chown=tracynth:tracynth infrastructure/caddy/frontend.Caddyfile /etc/caddy/Caddyfile
COPY --from=build --chown=tracynth:tracynth /build/dist/ /srv/

USER tracynth:tracynth
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["wget", "--quiet", "--spider", "http://127.0.0.1:8080/healthz"]

CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
