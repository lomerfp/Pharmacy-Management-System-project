from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from pharmacy.models import Batch, Category, Drug, Payment, Role, Sale, SaleItem, Staff, Supplier


class DashboardTests(TestCase):
    def setUp(self):
        role = Role.objects.create(name="Dashboard Manager", permissions=["dashboard.read"])
        self.staff = Staff.objects.create_user(username="manager", password="temporary-test-password-123", display_name="Demo Manager", role=role)
        self.client = APIClient()
        self.client.force_authenticate(user=self.staff)
        category = Category.objects.create(name="Dashboard category")
        supplier = Supplier.objects.create(name="Dashboard supplier")
        self.drug = Drug.objects.create(
            category=category, generic_name="Dashboard demo drug", strength="1 unit",
            dosage_form="Tablet", unit_of_measure="tablet", selling_price=Decimal("125.50"), reorder_level=5,
        )
        self.batch = Batch.objects.create(
            drug=self.drug, supplier=supplier, batch_number="DASHBOARD-LOT",
            expiry_date=timezone.localdate() + timedelta(days=60), received_quantity=4, available_quantity=4,
        )

    def test_summary_reconciles_completed_sale_and_sellable_stock(self):
        now = timezone.now()
        sale = Sale.objects.create(
            sale_number="DASH-SALE-001", processed_by=self.staff,
            status=Sale.Status.COMPLETED, completed_at=now,
            total_amount=Decimal("251.00"),
        )
        SaleItem.objects.create(
            sale=sale, batch=self.batch, quantity=2,
            unit_price=Decimal("125.50"), line_total=Decimal("251.00"),
        )
        Payment.objects.create(
            sale=sale, method=Payment.Method.CASH, amount=Decimal("251.00"),
            cash_tendered=Decimal("300.00"), change_given=Decimal("49.00"), recorded_by=self.staff,
        )

        response = self.client.get("/api/dashboard/summary/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["completed_sales"], 1)
        self.assertEqual(response.data["sales_total"], "251.00")
        self.assertEqual(response.data["payment_total"], "251.00")
        self.assertEqual(response.data["sellable_units"], 4)
        self.assertEqual(response.data["low_stock_drugs"][0]["available_units"], 4)
        self.assertEqual(response.data["top_selling_drugs"][0]["units"], 2)

    def test_dashboard_permission_is_enforced(self):
        role = Role.objects.create(name="Cashier dashboard test", permissions=["sales.checkout"])
        cashier = Staff.objects.create_user(username="dash-cashier", password="temporary-test-password-123", display_name="Demo Cashier", role=role)
        self.client.force_authenticate(user=cashier)

        response = self.client.get("/api/dashboard/summary/")

        self.assertEqual(response.status_code, 403)
