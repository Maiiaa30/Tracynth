# Security

Tracynth combines network reachability controls with application authentication.
Deploy it only on a host whose firewall rejects public traffic and bind Caddy to
the host's Tailscale address. Application login remains mandatory because any
permitted Tailnet device must still be treated as a separate trust boundary.

## Authentication and sessions

There is no registration endpoint. Create the first operator through the
documented management command. Django stores server-side sessions and sends an
HTTP-only cookie. Production settings require `Secure` and `SameSite=Lax`; CSRF
validation protects every unsafe browser request. Passwords use Argon2. Login
failures are throttled without logging the submitted identifier, and the
operator can invalidate all sessions.

Never expose Django development settings in production. Use a long random
`DJANGO_SECRET_KEY`, narrow `DJANGO_ALLOWED_HOSTS`, and configure the exact HTTPS
origin in `DJANGO_CSRF_TRUSTED_ORIGINS`.

## Network collection

Remote input is untrusted. URL handling must:

- accept only HTTP and HTTPS without embedded credentials;
- canonicalize hostnames and reject ambiguous representations;
- resolve and validate destinations and redirects against blocked IP classes;
- block loopback, private, link-local, multicast, unspecified, and metadata
  destinations unless a server-side internal-range policy explicitly allows them;
- stream within response-size, redirect, connect, read, and overall time limits;
- apply the same destination policy to browser automation and downloads.

`TRACYNTH_ALLOW_PRIVATE_NETWORKS` is false by default. It is an operator-side
deployment control and must never be mapped directly from ordinary API input.

## File processing

Uploads use generated storage identifiers; supplied filenames are display-only.
Originals are immutable. Sanitization always creates and re-analyzes a new file.
Parsers do not execute macros, scripts, formulas, attachments, or embedded
executables. Archive handling rejects traversal, symlinks, excessive nesting,
entry counts, expanded sizes, and compression ratios.

Evidence storage is private, authenticated, retention-controlled, and excluded
from source control and image build contexts. Authorized exposure imports use
isolated temporary storage, discard password/hash fields and unrelated rows,
retain only required redacted matches, and delete raw imports promptly.

## Secrets and logging

Secrets belong in the untracked `.env` file or a production secret mechanism.
Never place them in Git, images, fixtures, task arguments, browser storage, or
logs. Logs use stable record identifiers instead of submitted emails, usernames,
URLs containing queries, evidence excerpts, session values, or raw import data.

## Browser headers

Caddy and Django enforce a restrictive content security policy, frame denial,
MIME sniffing protection, strict referrer policy, and transport security. Any
new external frontend resource requires an explicit policy review; self-hosting
static assets is preferred.

## Reporting concerns

Report a suspected security issue privately to the repository owner. Do not add
sensitive evidence, proof data, credentials, or production identifiers to a
public issue.
