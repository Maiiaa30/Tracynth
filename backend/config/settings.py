from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


DEBUG = env_bool("DJANGO_DEBUG", False)
ENVIRONMENT = os.getenv("TRACYNTH_ENV", "development").strip().casefold()
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG or ENVIRONMENT in {"development", "test"}:
        SECRET_KEY = "development-only-change-me"
    else:
        raise ImproperlyConfigured("DJANGO_SECRET_KEY is required outside development/test")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "config.apps.ConfigConfig",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "accounts",
    "targets",
    "scans",
    "entities",
    "evidence",
    "findings",
    "incidents",
    "filelab",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "accounts.middleware.SessionVersionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

DATABASE_URL_IS_CONFIGURED = bool(os.getenv("DATABASE_URL") or os.getenv("POSTGRES_HOST"))
DATABASES: dict[str, object]
if os.getenv("POSTGRES_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "HOST": os.environ["POSTGRES_HOST"],
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
            "NAME": os.environ["POSTGRES_DB"],
            "USER": os.environ["POSTGRES_USER"],
            "PASSWORD": os.environ["POSTGRES_PASSWORD"],
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'db.sqlite3'}")
    DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=60)}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
MEDIA_ROOT = Path(os.getenv("TRACYNTH_EVIDENCE_ROOT", str(BASE_DIR / "var" / "evidence")))
MEDIA_URL = "/_not_public_/"

SESSION_COOKIE_NAME = "tracynth_session"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", not DEBUG)
SESSION_COOKIE_AGE = int(os.getenv("DJANGO_SESSION_AGE_SECONDS", "43200"))
CSRF_COOKIE_NAME = "tracynth_csrftoken"
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", not DEBUG)
CSRF_FAILURE_VIEW = "accounts.views.csrf_failure"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", False)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "0" if DEBUG else "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", False)
X_FRAME_OPTIONS = "DENY"


def built_redis_url(database: int) -> str:
    host = os.getenv("REDIS_HOST")
    if not host:
        return ""
    password = os.getenv("REDIS_PASSWORD", "")
    authentication = f":{quote(password, safe='')}@" if password else ""
    return f"redis://{authentication}{host}:{os.getenv('REDIS_PORT', '6379')}/{database}"


REDIS_URL = os.getenv("REDIS_URL") or built_redis_url(0)
TASK_COORDINATION_IS_CONFIGURED = bool(
    REDIS_URL or (os.getenv("CELERY_BROKER_URL") and os.getenv("CELERY_RESULT_BACKEND"))
)
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {"socket_connect_timeout": 2, "socket_timeout": 2},
        }
    }
else:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL") or built_redis_url(1) or REDIS_URL
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND") or built_redis_url(2) or REDIS_URL
if not CELERY_BROKER_URL:
    CELERY_BROKER_URL = "redis://localhost:6379/1"
if not CELERY_RESULT_BACKEND:
    CELERY_RESULT_BACKEND = "redis://localhost:6379/2"
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_RESULT_SERIALIZER = "json"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_ACKS_LATE = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_TIME_LIMIT = int(os.getenv("CELERY_TASK_TIME_LIMIT", "900"))
CELERY_TASK_SOFT_TIME_LIMIT = int(os.getenv("CELERY_TASK_SOFT_TIME_LIMIT", "840"))

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "config.api.StandardPagination",
    "PAGE_SIZE": 50,
    "EXCEPTION_HANDLER": "config.api.stable_exception_handler",
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

LOGIN_BACKOFF_BASE_SECONDS = int(os.getenv("LOGIN_BACKOFF_BASE_SECONDS", "2"))
LOGIN_BACKOFF_MAX_SECONDS = int(os.getenv("LOGIN_BACKOFF_MAX_SECONDS", "300"))
LOGIN_BACKOFF_THRESHOLD = int(os.getenv("LOGIN_BACKOFF_THRESHOLD", "3"))
LOGIN_GLOBAL_BACKOFF_THRESHOLD = int(os.getenv("LOGIN_GLOBAL_BACKOFF_THRESHOLD", "6"))
