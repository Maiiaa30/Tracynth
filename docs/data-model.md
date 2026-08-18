# Data model

The relational model uses UUID primary keys for externally referenced records
and database constraints for state and uniqueness invariants.

## Investigation records

- A `Target` represents a domain, URL, identity case, email, username, or file.
- A `ScanConfiguration` stores enabled modules and bounded collector settings.
- A `Scan` captures an immutable execution scope and aggregate lifecycle state.
- A `ScanModule` tracks one collector's progress, attempts, errors, and timing.
- A `MonitoringSchedule` creates future scans from a controlled schedule.

## Evidence graph

- An `Entity` stores an entity type, display value, normalized value, and state.
- A `Relationship` joins two entities with type, confidence, and review state.
- `Evidence` records provenance and optionally points to a controlled artifact.
- Relationship/evidence and finding/evidence join records preserve why a claim
  exists without embedding arbitrary remote content in graph rows.
- A `Finding` stores severity, confidence, explanation, remediation, lifecycle,
  verification, and first/last-seen timestamps.

## Files and incidents

- A `StoredFile` records a generated storage key, safe display name, hashes,
  detected MIME type, size, source, retention, and analysis state.
- A `FileMetadataEntry` stores typed extracted values with exact provenance.
- A sanitization relationship links an immutable original to a new derived file.
- An `Incident` stores credible public disclosure metadata and confidence.
- An `ExposureMatch` retains only authorized matching identifiers, redacted
  evidence, and provenance; raw imports remain temporary and excluded from
  normal backups.

## Operations

- `Alert` records new/changed/removed/reappeared observations and acknowledgement.
- `AuditEvent` stores security-relevant actions without secrets or submitted
  raw identifiers.
- `ApplicationSetting` stores non-secret operator policy. Secrets are environment
  variables or runtime secret files, never database values intended for display.

Indexes cover normalized entity values, target type/state, scan/module state and
timestamps, relationship endpoints, finding severity/status, alert state, and
full-text/trigram search columns. Migrations enable PostgreSQL `pg_trgm`.
