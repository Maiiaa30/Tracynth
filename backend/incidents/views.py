from rest_framework import viewsets

from .models import Incident
from .serializers import IncidentSerializer


class IncidentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Incident.objects.all()
    serializer_class = IncidentSerializer
