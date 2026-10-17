from .settings import *

PHARMACY_LEGACY_SCHEMA = False
MIGRATION_MODULES = {}

# Tests should use SQLite when explicitly requested or when DB_ENGINE is SQLite.
configured_engine = os.getenv("DB_ENGINE", "django.db.backends.mysql").strip()
if os.getenv("USE_SQLITE_TESTS", "").lower() == "true" or configured_engine in {"sqlite", "django.db.backends.sqlite3"}:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
else:
    DATABASES = {
        "default": {
            "ENGINE": configured_engine,
            "NAME": os.getenv("TEST_DB_NAME", os.getenv("DB_NAME", "pharmacy_management_db_test")),
            "USER": os.getenv("DB_USER", ""),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "127.0.0.1"),
            "PORT": os.getenv("DB_PORT", "3306"),
            "OPTIONS": {"charset": "utf8mb4"},
        }
    }
