from django.contrib import admin

from .models import FileMetadataEntry, SanitizationRelationship, StoredFile

admin.site.register(StoredFile)
admin.site.register(FileMetadataEntry)
admin.site.register(SanitizationRelationship)
