from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from pharmacy.models import AuditLog, Batch, Category, Drug, Role, Staff, StockMovement, Supplier


class ReportsAndAdjustmentsTests(TestCase):
    def setUp(self):
        self.report_role = Role.objects.create(name="Report Viewer", permissions=["reports.read", "inventory.adjust", "audit.read"])
        self.viewer = Staff.objects.create_user(username="reporter", password="temporary-test-password-123", display_name="Demo Report User", role=self.report_role)
        self.client = APIClient()
        self.client.force_authenticate(user=self.viewer)
        category = Category.objects.create(name="Reports test category")
        supplier = Supplier.objects.create(name="Reports test supplier")
        drug = Drug.objects.create(
            category=category, generic_name="Reports demo drug", strength="5 mg",
            dosage_form="Tablet", unit_of_measure="tablet", selling_price=Decimal("75.00"), reorder_level=2,
        )
        self.batch = Batch.objects.create(
            drug=drug, supplier=supplier, batch_number="REPORTS-LOT-01",
            expiry_date=timezone.localdate() + timedelta(days=90), received_quantity=10, available_quantity=10,
        )

    def test_stock_report_and_csv_export_are_role_protected_and_available(self):
        response = self.client.get("/api/reports/stock/")
        export = self.client.get("/api/reports/stock/?export=csv")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertTrue(response.data["results"][0]["sellable"])
        self.assertEqual(export.status_code, 200)
        self.assertEqual(export["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("REPORTS-LOT-01", export.content.decode())

        cashier_role = Role.objects.create(name="Reports denied", permissions=["sales.checkout"])
        cashier = Staff.objects.create_user(username="report-denied", password="temporary-test-password-123", display_name="Demo Cashier", role=cashier_role)
        self.client.force_authenticate(user=cashier)
        denied_json = self.client.get("/api/reports/stock/")
        denied_csv = self.client.get("/api/reports/stock/?export=csv")
        self.assertEqual(denied_json.status_code, 403)
        self.assertEqual(denied_csv.status_code, 403)

    def test_stock_adjustment_requires_reason_and_cannot_go_negative(self):
        short_reason = self.client.post(f"/api/batches/{self.batch.pk}/adjustments/", {"quantity_delta": -1, "reason": "bad"}, format="json")
        self.assertEqual(short_reason.status_code, 400)
        too_much = self.client.post(f"/api/batches/{self.batch.pk}/adjustments/", {"quantity_delta": -11, "reason": "Verified stock count difference"}, format="json")
        self.assertEqual(too_much.status_code, 400)

        response = self.client.post(f"/api/batches/{self.batch.pk}/adjustments/", {"quantity_delta": -2, "reason": "Verified count after inspection"}, format="json")

        self.assertEqual(response.status_code, 201)
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.available_quantity, 8)
        self.assertEqual(StockMovement.objects.filter(batch=self.batch, reason=StockMovement.Reason.ADJUSTMENT).count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="stock.adjusted", entity_id=str(self.batch.pk)).count(), 1)

    def test_audit_history_requires_explicit_audit_permission(self):
        AuditLog.objects.create(actor=self.viewer, action="test.event", entity_type="Test", entity_id="1", metadata={"safe": True})
        allowed = self.client.get("/api/audit/")
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.data["results"][0]["action"], "test.event")

        cashier_role = Role.objects.create(name="No audit access", permissions=["sales.checkout"])
        cashier = Staff.objects.create_user(username="no-audit", password="temporary-test-password-123", display_name="Demo Cashier", role=cashier_role)
        self.client.force_authenticate(user=cashier)
        denied = self.client.get("/api/audit/")
        self.assertEqual(denied.status_code, 403)
