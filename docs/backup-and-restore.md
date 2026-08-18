# Backup and restore

Back up PostgreSQL and controlled evidence storage together so database artifact
references remain consistent. Redis contains transient coordination state and is
not the authoritative investigation store.

Raw authorized-import staging areas and Django session rows are deliberately
excluded. Do not copy temporary uploads, task scratch space, `.env`, or TLS
private material into ordinary backups.

## Backup

Put investigations into a quiet window and run the supplied backup script:

```bash
python scripts/tracynth.py backup
```

The script resolves Compose service and volume names and produces an integrity
manifest. Encrypt the result with an organization-approved tool, store it outside the VPS, restrict
access, and apply retention. Check archive hashes after transfer.

## Restore drill

Restore into an isolated environment, never over a running production database:

```bash
docker compose down
# Recreate empty data volumes according to the documented recovery procedure.
docker compose up -d postgres redis
docker compose exec -T postgres pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists < backups/tracynth.dump
# Restore evidence.tar.gz into the evidence volume without changing ownership.
docker compose run --rm backend python manage.py migrate
docker compose up -d
```

For the managed in-place procedure, use
`python scripts/tracynth.py restore <backup-directory> --confirm-restore`. It
verifies the selected backup and creates a separate pre-restore safety backup
before replacing data. The switch is not fully atomic across PostgreSQL and the
evidence volume; retain the safety backup until all validation below succeeds.

Validate authentication, record counts, a representative evidence download,
graph relationships, and a report export. A backup is not considered healthy
until a restore drill succeeds. Record application revision, migration level,
backup hashes, encryption method, and drill result outside the backup archive.
