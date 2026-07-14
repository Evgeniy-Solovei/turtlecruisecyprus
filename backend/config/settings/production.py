from .base import *  # noqa: F403

DEBUG = False

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # Hashed filenames (app.abc123.js) → browser caches forever; deploy = new URL, no manual cache flush.
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Don't fail collectstatic if a CSS/JS file references a missing asset.
WHITENOISE_MANIFEST_STRICT = False

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", True)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", True)
SECURE_HSTS_SECONDS = int(env("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# Git snapshot is the only source of page HTML in production (no template fallbacks).
CMS_SNAPSHOT_REQUIRED = env_bool("CMS_SNAPSHOT_REQUIRED", True)
CMS_DISABLE_TEMPLATE_FALLBACK = env_bool("CMS_DISABLE_TEMPLATE_FALLBACK", True)
