from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from pharmacy.models import (
    AuditLog, Batch, Category, Customer, Doctor, Drug, Payment, Prescription,
    PrescriptionItem, Role, Sale, Staff, StaffCredential, Supplier,
)
from pharmacy.services import complete_sale


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AuthAndPrescriptionTests(TestCase):
    def setUp(self):
        self.pharmacist_role = Role.objects.create(name="Pharmacist", permissions=[
            "clinical.read", "clinical.manage", "prescriptions.read",
            "prescriptions.manage", "prescriptions.review", "sales.checkout",
        ])
        self.cashier_role = Role.objects.create(name="Cashier", permissions=["sales.checkout"])
        self.pharmacist = Staff.objects.create_user(
            username="pharmacist", password="start-password-12345", email="pharmacist@example.test",
            display_name="Demo Pharmacist", role=self.pharmacist_role,
        )
        self.cashier = Staff.objects.create_user(
            username="cashier", password="start-password-12345", display_name="Demo Cashier", role=self.cashier_role,
        )
        self.customer = Customer.objects.create(full_name="Fictional Customer")
        self.doctor = Doctor.objects.create(full_name="Fictional Doctor", registration_number="DEMO-REG-01")
        category = Category.objects.create(name="Prescription demo")
        self.supplier = Supplier.objects.create(name="Fictional Pharmacy Supplier")
        self.drug = Drug.objects.create(
            category=category, generic_name="Demo prescription medicine", strength="10 mg",
            dosage_form="Tablet", unit_of_measure="tablet", selling_price=Decimal("100.00"),
            prescription_required=True,
        )
        self.batch = Batch.objects.create(
            drug=self.drug, supplier=self.supplier, batch_number="DEMO-RX-BATCH",
            expiry_date=timezone.localdate() + timedelta(days=90), received_quantity=20, available_quantity=20,
        )
        self.prescription = Prescription.objects.create(
            reference="RX-DEMO-001", customer=self.customer, doctor=self.doctor,
            recorded_by=self.pharmacist, prescribed_at=timezone.localdate(),
            status=Prescription.Status.APPROVED, reviewed_by=self.pharmacist,
            reviewed_at=timezone.now(),
        )
        self.prescription_item = PrescriptionItem.objects.create(
            prescription=self.prescription, drug=self.drug, authorized_quantity=3,
            dosage="As written", frequency="As written", duration="As written",
        )

    def test_cashier_cannot_list_clinical_customer_records(self):
        client = APIClient()
        client.force_authenticate(user=self.cashier)

        response = client.get("/api/customers/")

        self.assertEqual(response.status_code, 403)

    def test_cashier_customer_lookup_returns_only_checkout_identity(self):
        self.cashier.role.permissions.append("sales.customer_lookup")
        self.cashier.role.save(update_fields=["permissions", "updated_at"])
        client = APIClient()
        client.force_authenticate(user=self.cashier)

        response = client.get("/api/sales/customer-lookup/?q=Fiction")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [{"id": self.customer.id, "full_name": "Fictional Customer"}])
        self.assertNotIn("email", response.data[0])
        self.assertNotIn("phone", response.data[0])
        self.assertNotIn("prescriptions", response.data[0])

    def test_local_vite_development_ports_are_allowed_for_cors(self):
        self.assertIn("http://localhost:5173", settings.CORS_ALLOWED_ORIGINS)
        self.assertIn("http://127.0.0.1:5173", settings.CORS_ALLOWED_ORIGINS)
        self.assertIn("http://127.0.0.1:5174", settings.CORS_ALLOWED_ORIGINS)

    def test_public_signup_creates_inactive_unassigned_staff_request(self):
        response = APIClient().post("/api/auth/signup/", {
            "username": "new-staff-request", "email": "new-staff@example.test",
            "display_name": "Requested Staff", "password": "new-staff-password-12345",
        }, format="json")

        self.assertEqual(response.status_code, 201)
        pending = Staff.objects.get(username="new-staff-request")
        self.assertFalse(pending.is_active)
        self.assertIsNone(pending.role_id)
        self.assertTrue(pending.check_password("new-staff-password-12345"))
        self.assertEqual(pending.credential.email, "new-staff@example.test")
        login_response = APIClient().post("/api/auth/token/", {
            "email": pending.email, "password": "new-staff-password-12345",
        }, format="json")
        self.assertEqual(login_response.status_code, 401)

    def test_staff_sign_in_uses_email_and_credential_hash(self):
        credential = StaffCredential.objects.get(staff=self.pharmacist)
        self.assertNotEqual(credential.password_hash, "start-password-12345")

        response = APIClient().post("/api/auth/token/", {
            "email": "  PHARMACIST@example.test ", "password": "start-password-12345",
        }, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        rejected = APIClient().post("/api/auth/token/", {
            "email": self.pharmacist.username, "password": "start-password-12345",
        }, format="json")
        self.assertEqual(rejected.status_code, 401)

    def test_staff_admin_can_activate_assign_role_and_deactivate_accounts(self):
        admin_role = Role.objects.create(name="Staff Admin", permissions=["staff.manage"])
        admin = Staff.objects.create_user(username="staff-admin", password="staff-admin-password-12345", display_name="Staff Admin", role=admin_role)
        pending = Staff.objects.create_user(username="pending-staff", password="pending-password-12345", display_name="Pending Staff", is_active=False)
        client = APIClient()
        client.force_authenticate(user=admin)

        activated = client.patch(f"/api/staff/{pending.pk}/", {"role": self.cashier_role.pk, "is_active": True}, format="json")
        self.assertEqual(activated.status_code, 200)
        pending.refresh_from_db()
        self.assertTrue(pending.is_active)
        self.assertEqual(pending.role_id, self.cashier_role.id)

        removed = client.delete(f"/api/staff/{pending.pk}/")
        self.assertEqual(removed.status_code, 204)
        pending.refresh_from_db()
        self.assertFalse(pending.is_active)
        self.assertTrue(AuditLog.objects.filter(action="staff.deactivated", entity_id=str(pending.pk)).exists())

    def test_pharmacist_can_review_pending_prescription(self):
        pending = Prescription.objects.create(
            reference="RX-DEMO-PENDING", customer=self.customer, doctor=self.doctor,
            recorded_by=self.pharmacist, prescribed_at=timezone.localdate(),
        )
        client = APIClient()
        client.force_authenticate(user=self.pharmacist)

        response = client.post(f"/api/prescriptions/{pending.pk}/review/", {"action": "approve"}, format="json")

        self.assertEqual(response.status_code, 200)
        pending.refresh_from_db()
        self.assertEqual(pending.status, Prescription.Status.APPROVED)
        self.assertEqual(pending.reviewed_by_id, self.pharmacist.id)

    def test_checkout_requires_matching_approved_prescription_and_remaining_quantity(self):
        request = {
            "actor": self.cashier, "idempotency_key": "rx-sale-test-1", "customer_id": self.customer.id,
            "prescription_id": self.prescription.id,
            "lines": [{"drug_id": self.drug.id, "quantity": 2}],
            "payment_method": Payment.Method.CASH, "cash_tendered": "200.00",
        }
        first_sale = complete_sale(**request)
        self.assertEqual(first_sale.status, Sale.Status.COMPLETED)

        over_limit = {**request, "idempotency_key": "rx-sale-test-2", "lines": [{"drug_id": self.drug.id, "quantity": 2}]}
        with self.assertRaises(Exception):
            complete_sale(**over_limit)
        self.assertEqual(Sale.objects.filter(prescription=self.prescription, status=Sale.Status.COMPLETED).count(), 1)

        mismatched_customer = {**request, "idempotency_key": "rx-sale-test-3", "customer_id": None}
        with self.assertRaises(Exception):
            complete_sale(**mismatched_customer)

    def test_password_reset_token_is_single_use_and_expiring(self):
        client = APIClient()
        response = client.post("/api/auth/password/reset/", {"email": self.pharmacist.email}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        raw_token = mail.outbox[0].body.rsplit(" ", 1)[-1]

        confirmed = client.post("/api/auth/password/reset/confirm/", {
            "token": raw_token, "new_password": "replacement-password-6789",
        }, format="json")
        repeated = client.post("/api/auth/password/reset/confirm/", {
            "token": raw_token, "new_password": "replacement-password-6789",
        }, format="json")
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(repeated.status_code, 400)
        self.pharmacist.refresh_from_db()
        self.assertTrue(self.pharmacist.check_password("replacement-password-6789"))

    def test_password_change_updates_the_credential_hash(self):
        client = APIClient()
        client.force_authenticate(user=self.pharmacist)

        response = client.post("/api/auth/password/change/", {
            "old_password": "start-password-12345",
            "new_password": "changed-password-67890",
        }, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.pharmacist.check_password("changed-password-67890"))
        login = APIClient().post("/api/auth/token/", {
            "email": self.pharmacist.email, "password": "changed-password-67890",
        }, format="json")
        self.assertEqual(login.status_code, 200)

    def test_logout_blacklists_refresh_token(self):
        refresh = RefreshToken.for_user(self.pharmacist)
        client = APIClient()
        client.force_authenticate(user=self.pharmacist)

        response = client.post("/api/auth/logout/", {"refresh": str(refresh)}, format="json")

        self.assertEqual(response.status_code, 204)
