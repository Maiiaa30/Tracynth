import os

from celery import Celery
from kombu import Exchange, Queue

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("tracynth")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.task_queues = tuple(
    Queue(name, Exchange(name, type="direct"), routing_key=name)
    for name in ("general", "crawler", "browser", "file")
)
app.conf.task_default_queue = "general"
app.conf.task_default_exchange = "general"
app.conf.task_default_routing_key = "general"
app.conf.task_routes = {
    "scans.tasks.*": {"queue": "general"},
    "collectors.crawler.*": {"queue": "crawler"},
    "collectors.browser.*": {"queue": "browser"},
    "filelab.tasks.*": {"queue": "file"},
}
app.autodiscover_tasks()
