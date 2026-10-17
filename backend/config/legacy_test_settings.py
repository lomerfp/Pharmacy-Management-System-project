from .test_settings import *

PHARMACY_LEGACY_SCHEMA = True
MIGRATION_MODULES = {"pharmacy": "pharmacy.migrations_legacy"}
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}