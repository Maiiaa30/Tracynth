from django.contrib import admin
from django.urls import include, path, re_path
from rest_framework.routers import DefaultRouter

from accounts.views import ApplicationSettingViewSet, health
from config.api import api_not_found
from entities.views import EntityViewSet, RelationshipViewSet
from evidence.views import EvidenceViewSet
from filelab.views import StoredFileViewSet
from findings.views import FindingViewSet
from incidents.views import IncidentViewSet
from scans.views import MonitoringScheduleViewSet, ScanViewSet
from targets.views import ScanConfigurationViewSet, TargetViewSet

router = DefaultRouter()
router.register("targets", TargetViewSet)
router.register("scan-configurations", ScanConfigurationViewSet)
router.register("scans", ScanViewSet)
router.register("monitoring", MonitoringScheduleViewSet, basename="monitoring")
router.register("entities", EntityViewSet)
router.register("relationships", RelationshipViewSet)
router.register("evidence", EvidenceViewSet)
router.register("findings", FindingViewSet)
router.register("files", StoredFileViewSet)
router.register("incidents", IncidentViewSet)
router.register("settings", ApplicationSettingViewSet)

urlpatterns = [
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("accounts.urls")),
    path("api/v1/", include(router.urls)),
    re_path(r"^api/.*$", api_not_found),
]
