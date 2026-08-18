from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .engine import transition_to_cancelled
from .models import MonitoringSchedule, Scan, ScanModule
from .serializers import MonitoringScheduleSerializer, ScanSerializer


class ScanViewSet(viewsets.ModelViewSet):
    queryset = Scan.objects.select_related("target", "configuration").prefetch_related("modules")
    serializer_class = ScanSerializer
    http_method_names = ("get", "post", "head", "options")

    def perform_create(self, serializer):
        from .tasks import enqueue_scan

        with transaction.atomic():
            scan = serializer.save(created_by=self.request.user)
            modules = scan.scope_snapshot.get("enabled_modules", [])
            ScanModule.objects.bulk_create(
                ScanModule(scan=scan, module=module, attempt=1) for module in modules
            )
            transaction.on_commit(lambda: enqueue_scan(str(scan.id)))

    @action(detail=True, methods=("post",))
    def cancel(self, request, pk=None):
        scan = self.get_object()
        if scan.state not in {Scan.State.QUEUED, Scan.State.RUNNING}:
            return Response(
                {
                    "error": {
                        "code": "scan_not_cancellable",
                        "message": "This scan is already terminal.",
                        "fields": {},
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )
        transition_to_cancelled(scan.id)
        scan.refresh_from_db()
        return Response(self.get_serializer(scan).data)


class MonitoringScheduleViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only until a scheduler backend is implemented."""

    queryset = MonitoringSchedule.objects.select_related("target", "configuration")
    serializer_class = MonitoringScheduleSerializer
    http_method_names = ("get", "head", "options")
