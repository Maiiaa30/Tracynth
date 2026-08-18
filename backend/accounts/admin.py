from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import ApplicationSetting, AuditEvent, User

admin.site.register(User, UserAdmin)
admin.site.register(AuditEvent)
admin.site.register(ApplicationSetting)
