from django.contrib import admin

from .models import ExposureMatch, Incident

admin.site.register(Incident)
admin.site.register(ExposureMatch)
