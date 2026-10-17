from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.management.base import CommandError
from django.db import transaction

from pharmacy.models import Role


DEFAULT_ROLES = {
    "Administrator": ["staff.manage", "settings.manage", "audit.read", "dashboard.read"],
    "Pharmacist/Manager": ["inventory.read", "inventory.manage", "purchasing.read", "purchasing.manage", "purchasing.receive", "clinical.read", "clinical.manage", "prescriptions.read", "prescriptions.manage", "prescriptions.review", "sales.checkout", "sales.read", "reports.read", "dashboard.read", "audit.read", "settings.manage"],
    "Pharmacy Technician": ["inventory.read", "prescriptions.read", "prescriptions.manage", "sales.checkout"],
    "Cashier": ["inventory.read", "sales.checkout", "sales.customer_lookup"],
    "Inventory Officer": ["inventory.read", "inventory.manage", "inventory.receive", "inventory.quarantine", "inventory.adjust", "purchasing.read", "purchasing.manage", "purchasing.receive", "dashboard.read", "reports.read"],
    "Owner/Manager": ["dashboard.read", "sales.read", "reports.read", "purchasing.read", "inventory.read", "audit.read"],
}


class Command(BaseCommand):
    help = "Create or update the standard role permissions for the single-location pharmacy."

    @transaction.atomic
    def handle(self, *args, **options):
        if settings.PHARMACY_LEGACY_SCHEMA:
            raise CommandError("Legacy role rows are read-only; role permissions use the built-in role mapping.")
        for name, permissions in DEFAULT_ROLES.items():
            role, created = Role.objects.update_or_create(
                name=name,
                defaults={"permissions": permissions, "is_active": True},
            )
            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} role: {role.name}")
        self.stdout.write(self.style.SUCCESS("Default role records are ready. Clinical permissions remain explicit."))
