from rest_framework import viewsets

from .models import StoredFile
from .serializers import StoredFileSerializer


class StoredFileViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StoredFile.objects.prefetch_related("metadata_entries").all()
    serializer_class = StoredFileSerializer
