from rest_framework import viewsets

from .models import Entity, Relationship
from .serializers import EntitySerializer, RelationshipSerializer


class EntityViewSet(viewsets.ModelViewSet):
    queryset = Entity.objects.all()
    serializer_class = EntitySerializer


class RelationshipViewSet(viewsets.ModelViewSet):
    queryset = Relationship.objects.select_related("source", "target").all()
    serializer_class = RelationshipSerializer
