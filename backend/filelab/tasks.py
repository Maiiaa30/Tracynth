from celery import shared_task


@shared_task(bind=True, name="filelab.tasks.analyze_file", acks_late=True)
def analyze_file(self, stored_file_id: str) -> None:
    """Bounded parser integration hook; only a generated file identifier crosses the queue."""

    from .models import StoredFile

    if not StoredFile.objects.filter(pk=stored_file_id).exists():
        return
