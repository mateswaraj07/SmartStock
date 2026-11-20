"""SmartStock settings. Secrets come from the .env file in the project root."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = os.environ.get("DJANGO_DEBUG", "False") == "True"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost").split(",")

# Only our own app: the database will contain exactly the 8 SmartStock tables
# (Django's built-in user/admin/session tables are not used).
INSTALLED_APPS = ["corsheaders", "rest_framework", "core"]
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
TEMPLATES = []

DATABASES = {"default": {
    "ENGINE": "django.db.backends.mysql",
    "NAME": os.environ.get("DB_NAME", "smartstock_final"),
    "USER": os.environ.get("DB_USER", "root"),
    "PASSWORD": os.environ["DB_PASSWORD"],
    "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
    "PORT": os.environ.get("DB_PORT", "3306"),
    "OPTIONS": {"charset": "utf8mb4"},
}}
# Passwords are hashed with Django's default PBKDF2 hasher.

TIME_ZONE = "Asia/Kolkata"
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["core.auth.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "UNAUTHENTICATED_USER": None,
}
CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",")
