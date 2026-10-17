import importlib
import os
import sys
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from pharmacy.models import Batch, Payment, Prescription, Role, Sale


class DemoSeedTests(TestCase):
    def test_mysql_configuration_uses_env_credentials(self):
        sys.modules.pop("config.settings", None)
        with patch.dict(os.environ, {
            "DB_ENGINE": "django.db.backends.mysql",
            "DB_NAME": "pharmacy_management_db",
            "DB_USER": "pharmacy_app",
            "DB_PASSWORD": "local-secret",
            "DB_HOST": "127.0.0.1",
            "DB_PORT": "3306",
        }, clear=True):
            settings_module = importlib.import_module("config.settings")
            self.assertEqual(settings_module.DATABASES["default"]["ENGINE"], "django.db.backends.mysql")
            self.assertEqual(settings_module.DATABASES["default"]["NAME"], "pharmacy_management_db")
            self.assertEqual(settings_module.DATABASES["default"]["PORT"], "3306")
        sys.modules.pop("config.settings", None)

    @override_settings(DEBUG=False)
    def test_demo_seed_refuses_non_debug_environment(self):
        with patch.dict(os.environ, {"DEMO_STAFF_PASSWORD": "demo-password-12345"}):
            with self.assertRaises(CommandError):
                call_command("seed_demo")

    @override_settings(DEBUG=True)
    def test_demo_seed_creates_fictional_roles_and_workflow_records(self):
        with patch.dict(os.environ, {"DEMO_STAFF_PASSWORD": "demo-password-12345"}):
            call_command("seed_demo", stdout=StringIO())
            call_command("seed_demo", stdout=StringIO())

        self.assertEqual(Role.objects.count(), 6)
        self.assertEqual(Batch.objects.count(), 7)
        self.assertTrue(Prescription.objects.filter(reference="DEMO-RX-001").exists())
        self.assertTrue(Sale.objects.filter(idempotency_key="demo-otc-sale-001", status=Sale.Status.COMPLETED).exists())
        self.assertEqual(Payment.objects.filter(sale__idempotency_key="demo-otc-sale-001").count(), 1)
        cashier_role = Role.objects.get(name="Cashier")
        self.assertNotIn("dashboard.read", cashier_role.permissions)
        self.assertNotIn("sales.read", cashier_role.permissions)
