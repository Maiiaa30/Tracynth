FROM caddy:2.11-alpine

RUN addgroup -S -g 10001 tracynth \
    && adduser -S -D -H -u 10001 -G tracynth tracynth \
    && setcap -r /usr/bin/caddy

COPY --chown=tracynth:tracynth infrastructure/caddy/Caddyfile /etc/caddy/Caddyfile

USER tracynth:tracynth
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["wget", "--quiet", "--spider", "http://127.0.0.1:8080/health/"]

CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
