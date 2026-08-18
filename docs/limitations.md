# Limitations

Tracynth is an evidence organization and passive exposure-review tool, not a
guarantee of ownership, identity, compromise, completeness, or current risk.
Remote sources can be unavailable, rate-limited, stale, inaccurate, or subject
to terms that restrict collection.

- Matching usernames do not prove that profiles belong to the same person.
- Image perceptual hashes measure visual similarity only; no facial recognition
  is performed.
- Certificate names, DNS links, and public emails are evidence-backed
  observations, not automatic ownership claims.
- Incident metadata does not prove that a specific identifier was affected.
  Exact exposure claims require an authorized underlying import match.
- File sanitization can remove only metadata supported reliably by installed
  libraries. Re-analysis reports remaining and unsupported risks.
- JavaScript rendering is selective and can still fail on complex or protected
  sites. CAPTCHA and access-control bypasses are out of scope.
- Private/internal network collection is blocked by default. Enabling a narrow
  server-side range requires an explicit deployment security review.
- A single-node Compose deployment does not provide automatic database failover
  or high availability. Tested encrypted backups and restore drills are required.

The interface must display source limitations and unsupported states rather than
substituting fabricated results or global risk scores.
