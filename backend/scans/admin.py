from django.contrib import admin

from .models import MonitoringSchedule, Scan, ScanModule

admin.site.register(Scan)
admin.site.register(ScanModule)
admin.site.register(MonitoringSchedule)
