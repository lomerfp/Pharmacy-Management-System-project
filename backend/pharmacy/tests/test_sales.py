from datetime import date, timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from pharmacy.models import Batch, Category, Drug, Payment, Role, Sale, SaleItem, Staff, StockMovement, Supplier
from pharmacy.services import complete_sale


class CheckoutServiceTests(TestCase):
    def setUp(self):
        role = Role.objects.create(name="Cashier", permissions=["sales.checkout"])
        self.staff = Staff.objects.create_user(username="cashier", password="temporary-test-password-123", display_name="Demo Cashier", role=role)
        category = Category.objects.create(name="Analgesics")
        self.supplier = Supplier.objects.create(name="Fictional Medical Supplies")
        self.drug = Drug.objects.create(
            category=category, generic_name="Demo paracetamol", strength="500 mg",
            dosage_form="Tablet", unit_of_measure="tablet", selling_price=Decimal("250.00"),
        )
        self.today = timezone.localdate()

    def add_batch(self, number, expiry, quantity):
        return Batch.objects.create(
            drug=self.drug, supplier=self.supplier, batch_number=number,
            expiry_date=expiry, received_quantity=quantity, available_quantity=quantity,
        )

    def test_fefo_splits_quantity_and_supports_anonymous_otc(self):
        later = self.add_batch("LOT-LATER", self.today + timedelta(days=100), 5)
        sooner = self.add_batch("LOT-SOONER", self.today + timedelta(days=20), 2)

        sale = complete_sale(
            actor=self.staff, idempotency_key="checkout-fefo-001", customer_id=None,
            prescription_id=None, lines=[{"drug_id": self.drug.pk, "quantity": 4}],
            payment_method=Payment.Method.CASH, cash_tendered="1250.00",
        )

        sale_items = list(SaleItem.objects.filter(sale=sale).order_by("id"))
        sooner.refresh_from_db()
        later.refresh_from_db()
        self.assertEqual(sale.status, Sale.Status.COMPLETED)
        self.assertIsNone(sale.customer_id)
        self.assertEqual([(item.batch_id, item.quantity) for item in sale_items], [(sooner.pk, 2), (later.pk, 2)])
        self.assertEqual(sale.total_amount, Decimal("1000.00"))
        self.assertEqual(sale.payment.change_given, Decimal("250.00"))
        self.assertEqual(sooner.available_quantity, 0)
        self.assertEqual(later.available_quantity, 3)
        self.assertEqual(StockMovement.objects.filter(reference=sale.sale_number).count(), 2)

    def test_expired_batch_rejected_without_persisting_sale_or_stock_change(self):
        expired = self.add_batch("LOT-EXPIRED", self.today - timedelta(days=1), 10)

        with self.assertRaises(Exception):
            complete_sale(
                actor=self.staff, idempotency_key="checkout-expired-001", customer_id=None,
                prescription_id=None, lines=[{"drug_id": self.drug.pk, "quantity": 1}],
                payment_method=Payment.Method.CASH, cash_tendered="250.00",
            )

        expired.refresh_from_db()
        self.assertEqual(expired.available_quantity, 10)
        self.assertFalse(Sale.objects.filter(idempotency_key="checkout-expired-001").exists())
        self.assertFalse(Payment.objects.exists())

    def test_duplicate_batch_number_is_scoped_to_drug(self):
        self.add_batch("SHARED-MANUFACTURER-LOT", self.today + timedelta(days=40), 1)
        second_drug = Drug.objects.create(
            category=self.drug.category, generic_name="Demo ibuprofen", strength="200 mg",
            dosage_form="Tablet", unit_of_measure="tablet", selling_price=Decimal("300.00"),
        )
        Batch.objects.create(
            drug=second_drug, supplier=self.supplier, batch_number="SHARED-MANUFACTURER-LOT",
            expiry_date=self.today + timedelta(days=40), received_quantity=1, available_quantity=1,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Batch.objects.create(
                drug=self.drug, supplier=self.supplier, batch_number="SHARED-MANUFACTURER-LOT",
                expiry_date=self.today + timedelta(days=40), received_quantity=1, available_quantity=1,
            )

    def test_repeated_checkout_key_does_not_deduct_stock_twice(self):
        batch = self.add_batch("LOT-IDEMPOTENT", self.today + timedelta(days=50), 5)
        request = {
            "actor": self.staff, "idempotency_key": "checkout-repeat-001", "customer_id": None,
            "prescription_id": None, "lines": [{"drug_id": self.drug.pk, "quantity": 2}],
            "payment_method": Payment.Method.CASH, "cash_tendered": "500.00",
        }

        first = complete_sale(**request)
        repeated = complete_sale(**request)

        batch.refresh_from_db()
        self.assertEqual(first.pk, repeated.pk)
        self.assertEqual(batch.available_quantity, 3)
        self.assertEqual(Sale.objects.filter(idempotency_key="checkout-repeat-001").count(), 1)
        self.assertEqual(Payment.objects.filter(sale=first).count(), 1)
