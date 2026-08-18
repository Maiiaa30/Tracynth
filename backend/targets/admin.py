from django.contrib import admin

from .models import ScanConfiguration, Target

admin.site.register(Target)
admin.site.register(ScanConfiguration)
