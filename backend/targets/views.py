from rest_framework import viewsets

from .models import ScanConfiguration, Target
from .serializers import ScanConfigurationSerializer, TargetSerializer


class TargetViewSet(viewsets.ModelViewSet):
    queryset = Target.objects.all()
    serializer_class = TargetSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ScanConfigurationViewSet(viewsets.ModelViewSet):
    queryset = ScanConfiguration.objects.select_related("target").all()
    serializer_class = ScanConfigurationSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
