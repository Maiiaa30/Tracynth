from rest_framework import viewsets

from .models import Evidence
from .serializers import EvidenceSerializer


class EvidenceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Evidence.objects.select_related("scan", "target", "entity").all()
    serializer_class = EvidenceSerializer
