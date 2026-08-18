from django.conf import settings
from django.core.checks import Error, Tags, register


@register(Tags.security, deploy=True)
def production_configuration_check(app_configs, **kwargs):
    errors = []
    if settings.SECRET_KEY == "development-only-change-me":
        errors.append(Error("A development SECRET_KEY is configured.", id="tracynth.E001"))
    if settings.ENVIRONMENT == "production" and not settings.SESSION_COOKIE_SECURE:
        errors.append(Error("Secure session cookies are disabled.", id="tracynth.E002"))
    if settings.ENVIRONMENT == "production" and not settings.DATABASE_URL_IS_CONFIGURED:
        errors.append(Error("DATABASE_URL is required in production.", id="tracynth.E003"))
    if settings.ENVIRONMENT == "production" and not settings.TASK_COORDINATION_IS_CONFIGURED:
        errors.append(
            Error(
                "REDIS_URL or explicit Celery broker/result URLs are required in production.",
                id="tracynth.E004",
            )
        )
    return errors
