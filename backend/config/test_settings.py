from .settings import *

# Fast unit-test database only; PostgreSQL remains the default runtime database for integration work.
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
