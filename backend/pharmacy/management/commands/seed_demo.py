import os
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from pharmacy.management.commands.bootstrap_roles import DEFAULT_ROLES
from pharmacy.models import (
    Batch, Category, Customer, Doctor, Drug, Payment, Prescription,
    PrescriptionItem, PurchaseOrder, PurchaseOrderItem, Role, Sale, Staff,
    Supplier,
)
from pharmacy.services import complete_sale, receive_purchase_order


class Command(BaseCommand):
    help = "Create fictional, repeatable local demonstration records. Requires DEBUG=true and DEMO_STAFF_PASSWORD."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Refusing to seed demo data unless DJANGO_DEBUG=true.")
        password = os.getenv("DEMO_STAFF_PASSWORD", "")
        if len(password) < 12:
            raise CommandError("Set DEMO_STAFF_PASSWORD to a development-only password of at least 12 characters.")

        roles = {}
        for name, permissions in DEFAULT_ROLES.items():
            role, _ = Role.objects.update_or_create(name=name, defaults={"permissions": permissions, "is_active": True})
            roles[name] = role
        staff_rows = {}
        staff_specs = [
            ("demo_admin", "Demo Administrator", "Administrator"),
            ("demo_pharmacist", "Demo Pharmacist", "Pharmacist/Manager"),
            ("demo_technician", "Demo Technician", "Pharmacy Technician"),
            ("demo_cashier", "Demo Cashier", "Cashier"),
            ("demo_inventory", "Demo Inventory Officer", "Inventory Officer"),
            ("demo_owner", "Demo Owner Manager", "Owner/Manager"),
        ]
        for username, display_name, role_name in staff_specs:
            staff, created = Staff.objects.get_or_create(
                username=username,
                defaults={"display_name": display_name, "role": roles[role_name], "is_active": True},
            )
            if created:
                staff.set_password(password)
                staff.save(update_fields=["password"])
            else:
                staff.display_name = display_name
                staff.role = roles[role_name]
                staff.is_active = True
                staff.save(update_fields=["display_name", "role", "is_active", "updated_at"])
            staff_rows[username] = staff

        supplier, _ = Supplier.objects.get_or_create(name="Fictional Demo Medical Supplies", defaults={"contact_name": "Demo Contact", "phone": "+256 700 000 001", "email": "supplier@example.test", "address": "Fictional address, Kampala"})
        category, _ = Category.objects.get_or_create(name="Demo Essential Medicines", defaults={"description": "Fictional data for development and testing"})
        drug_specs = [
            ("Demo paracetamol", "500 mg", "Tablet", "tablet", "250.00", False, 8),
            ("Demo amoxicillin", "250 mg", "Capsule", "capsule", "600.00", True, 10),
            ("Demo oral rehydration salts", "standard", "Powder", "sachet", "500.00", False, 5),
            ("Demo ibuprofen", "200 mg", "Tablet", "tablet", "350.00", False, 4),
            ("Demo cetirizine", "10 mg", "Tablet", "tablet", "400.00", False, 6),
        ]
        drugs = {}
        for generic_name, strength, form, unit, price, requires_rx, reorder in drug_specs:
            drug, _ = Drug.objects.get_or_create(
                category=category, generic_name=generic_name, strength=strength,
                dosage_form=form, unit_of_measure=unit,
                defaults={"selling_price": Decimal(price), "prescription_required": requires_rx, "reorder_level": reorder},
            )
            drugs[generic_name] = drug

        today = timezone.localdate()
        batches = [
            ("DEMO-PARA-EXPIRING", drugs["Demo paracetamol"], today + timedelta(days=18), 8, 8, Batch.Status.AVAILABLE),
            ("DEMO-PARA-FUTURE", drugs["Demo paracetamol"], today + timedelta(days=220), 15, 12, Batch.Status.AVAILABLE),
            ("DEMO-AMOX-LOW", drugs["Demo amoxicillin"], today + timedelta(days=140), 10, 2, Batch.Status.AVAILABLE),
            ("DEMO-ORS-EXPIRED", drugs["Demo oral rehydration salts"], today - timedelta(days=1), 6, 6, Batch.Status.AVAILABLE),
            ("DEMO-IBU-QUARANTINED", drugs["Demo ibuprofen"], today + timedelta(days=180), 10, 10, Batch.Status.QUARANTINED),
            ("DEMO-CET-EMPTY", drugs["Demo cetirizine"], today + timedelta(days=100), 5, 0, Batch.Status.AVAILABLE),
        ]
        for batch_number, drug, expiry, received, available, status in batches:
            Batch.objects.get_or_create(
                drug=drug, batch_number=batch_number,
                defaults={"supplier": supplier, "expiry_date": expiry, "received_quantity": received, "available_quantity": available, "status": status},
            )

        customer, _ = Customer.objects.get_or_create(full_name="Demo Customer One", defaults={"phone": "+256 700 000 002", "email": "customer@example.test"})
        doctor, _ = Doctor.objects.get_or_create(registration_number="DEMO-DOCTOR-001", defaults={"full_name": "Demo Prescriber", "contact_phone": "+256 700 000 003"})
        prescription, created = Prescription.objects.get_or_create(
            reference="DEMO-RX-001",
            defaults={"customer": customer, "doctor": doctor, "recorded_by": staff_rows["demo_pharmacist"], "prescribed_at": today, "status": Prescription.Status.APPROVED, "reviewed_by": staff_rows["demo_pharmacist"], "reviewed_at": timezone.now()},
        )
        if created:
            PrescriptionItem.objects.create(
                prescription=prescription, drug=drugs["Demo amoxicillin"], authorized_quantity=6,
                dosage="As written by fictional prescriber", frequency="As written", duration="As written",
                instructions="Fictional demonstration instruction; not medical advice.",
            )

        po, _ = PurchaseOrder.objects.get_or_create(
            order_number="DEMO-PO-001",
            defaults={"supplier": supplier, "created_by": staff_rows["demo_inventory"], "status": PurchaseOrder.Status.ORDERED, "ordered_at": timezone.now()},
        )
        po_item, _ = PurchaseOrderItem.objects.get_or_create(
            purchase_order=po, drug=drugs["Demo paracetamol"],
            defaults={"ordered_quantity": 20, "unit_cost": Decimal("140.00")},
        )
        if not po.receipts.exists():
            receive_purchase_order(
                actor=staff_rows["demo_inventory"], purchase_order_id=po.pk, request_key="demo-receipt-001",
                items=[{"purchase_order_item_id": po_item.pk, "quantity": 10, "batch_number": "DEMO-RECEIVED-BATCH", "expiry_date": (today + timedelta(days=300)).isoformat()}],
            )

        sale_key = "demo-otc-sale-001"
        if not Sale.objects.filter(idempotency_key=sale_key).exists():
            complete_sale(
                actor=staff_rows["demo_cashier"], idempotency_key=sale_key, customer_id=None,
                prescription_id=None, lines=[{"drug_id": drugs["Demo paracetamol"].pk, "quantity": 1}],
                payment_method=Payment.Method.CASH, cash_tendered=drugs["Demo paracetamol"].selling_price,
            )

        self.stdout.write(self.style.SUCCESS("Fictional pharmacy demo data is ready."))
        self.stdout.write("Staff usernames: " + ", ".join(username for username, _, _ in staff_specs))
        self.stdout.write("All demo staff accounts share DEMO_STAFF_PASSWORD; use only in local development.")
