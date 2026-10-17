from getpass import getpass

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from pharmacy.models import Staff, set_staff_password


class Command(BaseCommand):
    help = "Set or replace a staff login password without modifying the legacy staff row."

    def add_arguments(self, parser):
        parser.add_argument("email")

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.PHARMACY_LEGACY_SCHEMA:
            raise CommandError("This command is reserved for PHARMACY_LEGACY_SCHEMA=true.")
        email = options["email"].strip()
        staff = Staff.objects.filter(email__iexact=email).first()
        if not staff:
            raise CommandError("No legacy staff row matches that email.")
        if not staff.is_active:
            raise CommandError("Inactive staff cannot receive login credentials.")

        password = getpass("New staff password: ")
        confirmation = getpass("Confirm password: ")
        if password != confirmation:
            raise CommandError("The passwords did not match.")
        try:
            validate_password(password, staff)
        except Exception as error:
            raise CommandError(str(error)) from error

        set_staff_password(staff, password)
        self.stdout.write(self.style.SUCCESS(f"Credentials saved for {staff.email}."))