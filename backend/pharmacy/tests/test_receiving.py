from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from pharmacy.models import Batch, Category, Drug, PurchaseOrder, PurchaseOrderItem, Role, Staff, Supplier
from pharmacy.services import receive_purchase_order


class ReceivingServiceTests(TestCase):
    def setUp(self):
        role = Role.objects.create(name="Inventory Officer", permissions=["purchasing.receive"])
        self.staff = Staff.objects.create_user(username="inventory", password="temporary-test-password-123", display_name="Demo Inventory Officer", role=role)
        self.supplier = Supplier.objects.create(name="Fictional Wholesale Supplier")
        category = Category.objects.create(name="Demo category")
        self.drug = Drug.objects.create(
            category=category, generic_name="Demo oral rehydration salts", strength="standard",
            dosage_form="Powder", unit_of_measure="sachet", selling_price=Decimal("500.00"),
        )
        self.order = PurchaseOrder.objects.create(
            order_number="PO-DEMO-001", supplier=self.supplier, created_by=self.staff,
            status=PurchaseOrder.Status.ORDERED,
        )
        self.item = PurchaseOrderItem.objects.create(
            purchase_order=self.order, drug=self.drug, ordered_quantity=10,
            unit_cost=Decimal("300.00"),
        )
        self.expiry = timezone.localdate() + timedelta(days=180)

    def test_partial_receipts_add_stock_only_once_and_complete_order(self):
        first_items = [{
            "purchase_order_item_id": self.item.pk, "quantity": 4,
            "batch_number": "DEMO-RECEIPT-A", "expiry_date": self.expiry.isoformat(),
        }]
        first = receive_purchase_order(
            actor=self.staff, purchase_order_id=self.order.pk,
            request_key="receipt-demo-001", items=first_items,
        )
        repeated = receive_purchase_order(
            actor=self.staff, purchase_order_id=self.order.pk,
            request_key="receipt-demo-001", items=first_items,
        )
        self.order.refresh_from_db()
        self.assertEqual(first.pk, repeated.pk)
        self.assertEqual(self.order.status, PurchaseOrder.Status.PARTIAL)
        self.assertEqual(Batch.objects.get(batch_number="DEMO-RECEIPT-A").available_quantity, 4)

        receive_purchase_order(
            actor=self.staff, purchase_order_id=self.order.pk,
            request_key="receipt-demo-002", items=[{
                "purchase_order_item_id": self.item.pk, "quantity": 6,
                "batch_number": "DEMO-RECEIPT-B", "expiry_date": self.expiry.isoformat(),
            }],
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, PurchaseOrder.Status.RECEIVED)
        self.assertEqual(Batch.objects.get(batch_number="DEMO-RECEIPT-B").available_quantity, 6)

    def test_over_receipt_rolls_back_without_creating_stock(self):
        with self.assertRaises(Exception):
            receive_purchase_order(
                actor=self.staff, purchase_order_id=self.order.pk,
                request_key="receipt-over-001", items=[{
                    "purchase_order_item_id": self.item.pk, "quantity": 11,
                    "batch_number": "DEMO-OVER-RECEIPT", "expiry_date": self.expiry.isoformat(),
                }],
            )

        self.assertFalse(Batch.objects.filter(batch_number="DEMO-OVER-RECEIPT").exists())
        self.assertFalse(self.order.receipts.exists())
