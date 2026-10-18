"""Django settings for Postmanager. All secrets come from environment variables (see .env.example)."""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).lower() in ("1", "true", "yes", "on")


# Running on Vercel (serverless): no disk, no background process. See README → "Vercel".
SERVERLESS = bool(os.environ.get("VERCEL"))
VERCEL_HOSTS = [h for h in (os.environ.get("VERCEL_PROJECT_PRODUCTION_URL"), os.environ.get("VERCEL_URL")) if h]

DEBUG = env_bool("DEBUG", not SERVERLESS)
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-change-me" if DEBUG else "")
if not SECRET_KEY:
    raise RuntimeError("Set the SECRET_KEY environment variable.")
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]
ALLOWED_HOSTS += VERCEL_HOSTS

# Public base URL of this site, e.g. https://studio-posts.vercel.app
# Instagram downloads media from here (unless files are in Vercel Blob), so it must be reachable online.
SITE_URL = os.environ.get(
    "SITE_URL", f"https://{VERCEL_HOSTS[0]}" if VERCEL_HOSTS else "http://localhost:8000",
).rstrip("/")
CSRF_TRUSTED_ORIGINS = [SITE_URL] if SITE_URL.startswith("https://") else []

# Secret for the scheduler link that an external timer calls (/cron/tick/). Vercel Cron sends it as a Bearer token.
CRON_SECRET = os.environ.get("CRON_SECRET", "")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "studio",  # before allauth so our sign-in/sign-up templates take precedence
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "studio.middleware.ApprovalMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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
                "studio.context_processors.studio",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Neon (via the Vercel integration) sets DATABASE_URL; older Vercel Postgres setups set POSTGRES_URL.
if not os.environ.get("DATABASE_URL") and os.environ.get("POSTGRES_URL"):
    os.environ["DATABASE_URL"] = os.environ["POSTGRES_URL"]
if SERVERLESS and not os.environ.get("DATABASE_URL"):
    raise RuntimeError("No database: connect a Neon Postgres database to the Vercel project (Storage tab).")
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=0 if SERVERLESS else 600,
        conn_health_checks=True,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Greek by default; each person can switch to English (menu → language).
LANGUAGE_CODE = "el"
LANGUAGES = [("el", "Ελληνικά"), ("en", "English")]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = os.environ.get("TIME_ZONE", "Europe/Athens")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = None if SERVERLESS else BASE_DIR / "staticfiles"
# Vercel Blob for uploads when its token is set (required on Vercel, which has no disk).
BLOB_READ_WRITE_TOKEN = os.environ.get("BLOB_READ_WRITE_TOKEN", "")
STORAGES = {
    "default": {
        "BACKEND": "studio.storage.VercelBlobStorage" if BLOB_READ_WRITE_TOKEN
        else "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage" if DEBUG or SERVERLESS
        else "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
# On Vercel there is no collectstatic step, so WhiteNoise serves straight from the app folders.
WHITENOISE_USE_FINDERS = SERVERLESS
WHITENOISE_MAX_AGE = 3600
# Changes with every Vercel deployment so browsers fetch fresh CSS/JS (see ?v= in templates).
STATIC_VERSION = os.environ.get("VERCEL_DEPLOYMENT_ID", "")[-12:] or "dev"

MEDIA_URL = "/media/"
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", BASE_DIR / "media"))
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# --- Accounts: email + password, or Google. New people wait for an owner's approval. ---
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "dashboard"
ACCOUNT_LOGOUT_REDIRECT_URL = "account_login"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_UNIQUE_EMAIL = True
# "optional" sends a confirmation email but doesn't block login; "mandatory" requires it (needs working email).
ACCOUNT_EMAIL_VERIFICATION = os.environ.get("ACCOUNT_EMAIL_VERIFICATION", "optional")
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https" if SITE_URL.startswith("https://") else "http"
ACCOUNT_EMAIL_SUBJECT_PREFIX = f"[{os.environ.get('STUDIO_NAME', 'Studio')} Posts] "
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True  # Google login finds an existing account with the same email
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_PROVIDERS = {}
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    SOCIALACCOUNT_PROVIDERS["google"] = {
        "APPS": [{"client_id": GOOGLE_CLIENT_ID, "secret": GOOGLE_CLIENT_SECRET, "key": ""}],
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"prompt": "select_account"},
    }

# Emails that become approved owners as soon as they sign up (comma separated).
# If empty, the very first account created becomes the owner.
OWNER_EMAILS = {e.strip().lower() for e in os.environ.get("OWNER_EMAILS", "").split(",") if e.strip()}

# --- Email (sign-up confirmations, password resets, new-member alerts) ---
# Without EMAIL_HOST, emails are printed to the server console instead of being sent.
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend" if EMAIL_HOST
    else "django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "noreply@localhost")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# --- Instagram (Meta app, "Instagram API with Instagram Login") ---
INSTAGRAM_APP_ID = os.environ.get("INSTAGRAM_APP_ID", "")
INSTAGRAM_APP_SECRET = os.environ.get("INSTAGRAM_APP_SECRET", "")
INSTAGRAM_API_VERSION = os.environ.get("INSTAGRAM_API_VERSION", "v23.0")

# --- AI captions (Claude). Leave ANTHROPIC_API_KEY empty to disable. ---
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CAPTION_MODEL = os.environ.get("CAPTION_MODEL", "claude-opus-5-5")
STUDIO_NAME = os.environ.get("STUDIO_NAME", "Our Dance Studio")
# Short description of the studio's voice, used as context when writing captions.
STUDIO_VOICE = os.environ.get(
    "STUDIO_VOICE",
    "Warm, energetic and welcoming. We teach all ages and levels. Use a few relevant emojis.",
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
