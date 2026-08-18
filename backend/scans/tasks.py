from celery import shared_task


@shared_task(bind=True, name="scans.tasks.orchestrate_scan", acks_late=True)
def orchestrate_scan(self, scan_id: str) -> None:
    """Run an idempotent scan; the task payload contains an identifier only."""

    from .engine import execute_scan

    execute_scan(scan_id)


def enqueue_scan(scan_id: str) -> bool:
    """Dispatch safely and terminally record a broker failure."""

    try:
        orchestrate_scan.delay(scan_id)
    except Exception:
        from .engine import mark_enqueue_failure

        mark_enqueue_failure(scan_id)
        return False
    return True
