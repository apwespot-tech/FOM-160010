import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

TRUE_VALUES = {"1", "on", "true", "yes"}


def read_required_variable(name: str) -> str:
    value = os.environ.get(name, "").strip()

    if not value:
        raise ImproperlyConfigured(f"Не задана переменная окружения {name}")

    return value


def read_optional_variable(name: str, default: str) -> str:
    value = os.environ.get(name, "").strip()

    if not value:
        return default

    return value


def read_flag(name: str, default: bool) -> bool:
    value = os.environ.get(name, "").strip().lower()

    if not value:
        return default

    return value in TRUE_VALUES


def read_list(name: str, default: str) -> list[str]:
    raw_value = read_optional_variable(name, default)
    items = [item.strip() for item in raw_value.split(",")]

    return [item for item in items if item]


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = read_required_variable("DJANGO_SECRET_KEY")
DEBUG = read_flag("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = read_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = read_list("DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost:5173")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.messages",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "finance_planner.urls"
WSGI_APPLICATION = "finance_planner.wsgi.application"
ASGI_APPLICATION = "finance_planner.asgi.application"

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
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": read_required_variable("POSTGRES_DB"),
        "USER": read_required_variable("POSTGRES_USER"),
        "PASSWORD": read_required_variable("POSTGRES_PASSWORD"),
        "HOST": read_optional_variable("POSTGRES_HOST", "db"),
        "PORT": read_optional_variable("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "connect_timeout": 3,
        },
    },
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = read_optional_variable("DJANGO_TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
