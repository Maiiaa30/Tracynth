from rest_framework import viewsets

from .models import Finding
from .serializers import FindingSerializer


class FindingViewSet(viewsets.ModelViewSet):
    queryset = Finding.objects.select_related("scan", "affected_entity").all()
    serializer_class = FindingSerializer
