from collections import defaultdict
from datetime import date
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import (
    AuditLog, Batch, Customer, Drug, GoodsReceipt, GoodsReceiptItem, Payment,
    Prescription, PrescriptionItem, PurchaseOrder, PurchaseOrderItem, Sale,
    SaleItem, StockMovement, Staff,
)


@transaction.atomic
def complete_sale(*, actor, idempotency_key, customer_id, prescription_id, lines, payment_method, payment_reference="", cash_tendered=None):
    if not idempotency_key:
        raise ValidationError({"idempotency_key": "This value is required."})
    sale, created = Sale.objects.get_or_create(
        idempotency_key=idempotency_key,
        defaults={
            "sale_number": f"S-{uuid4().hex[:20].upper()}",
            "processed_by": actor,
            "status": Sale.Status.DRAFT,
        },
    )
    if not created:
        if sale.status == Sale.Status.COMPLETED:
            return sale
        raise ValidationError({"idempotency_key": "A request with this key is already being processed."})
    if not lines:
        raise ValidationError({"items": "A sale must contain at least one item."})

    customer = None
    if customer_id is not None:
        customer = Customer.objects.select_for_update().filter(pk=customer_id, is_active=True).first()
        if not customer:
            raise ValidationError({"customer": "Customer is unavailable."})

    prescription = None
    if prescription_id is not None:
        prescription = Prescription.objects.select_for_update().filter(pk=prescription_id).first()
        if not prescription or prescription.status != Prescription.Status.APPROVED:
            raise ValidationError({"prescription": "A reviewed, approved prescription is required."})
        if customer is None or prescription.customer_id != customer.id:
            raise ValidationError({"customer": "Sale customer must match the prescription customer."})

    requested = defaultdict(int)
    for line in lines:
        try:
            drug_id = int(line["drug_id"])
            quantity = int(line["quantity"])
        except (KeyError, TypeError, ValueError):
            raise ValidationError({"items": "Each item requires an integer drug_id and positive quantity."})
        if quantity < 1:
            raise ValidationError({"items": "Quantities must be positive whole stock units."})
        requested[drug_id] += quantity

    drugs = {drug.id: drug for drug in Drug.objects.select_for_update().filter(id__in=requested).order_by("id")}
    if len(drugs) != len(requested):
        raise ValidationError({"items": "One or more drugs do not exist."})
    for drug in drugs.values():
        if drug.status != Drug.Status.ACTIVE:
            raise ValidationError({"items": f"{drug.generic_name} is inactive."})
        if drug.prescription_required and prescription is None:
            raise ValidationError({"prescription": f"A valid prescription is required for {drug.generic_name}."})

    prescription_items = {}
    if prescription:
        prescription_items = {
            item.drug_id: item for item in PrescriptionItem.objects.select_for_update()
            .filter(prescription=prescription, drug_id__in=requested).order_by("drug_id")
        }
        for drug_id, quantity in requested.items():
            item = prescription_items.get(drug_id)
            if drugs[drug_id].prescription_required:
                if not item:
                    raise ValidationError({"prescription": "The prescription does not authorize this drug."})
                dispensed = SaleItem.objects.filter(
                    sale__prescription=prescription, sale__status=Sale.Status.COMPLETED, batch__drug_id=drug_id,
                ).aggregate(total=Sum("quantity"))["total"] or 0
                if dispensed + quantity > item.authorized_quantity:
                    raise ValidationError({"prescription": f"Requested quantity exceeds remaining authorization for {drugs[drug_id].generic_name}."})

    today = timezone.now().astimezone(ZoneInfo(settings.BUSINESS_TIME_ZONE)).date()
    eligible = list(Batch.objects.select_for_update().filter(
        drug_id__in=requested, status=Batch.Status.AVAILABLE, available_quantity__gt=0,
        expiry_date__gte=today, drug__status=Drug.Status.ACTIVE,
    ).order_by("expiry_date", "id"))
    batches_by_drug = defaultdict(list)
    for batch in eligible:
        batches_by_drug[batch.drug_id].append(batch)
    allocations = []
    for drug_id, quantity in requested.items():
        remainder = quantity
        for batch in batches_by_drug[drug_id]:
            take = min(batch.available_quantity, remainder)
            if take:
                allocations.append((batch, take, drugs[drug_id]))
                remainder -= take
            if remainder == 0:
                break
        if remainder:
            raise ValidationError({"stock": f"Insufficient sellable stock for {drugs[drug_id].generic_name}."})

    total = sum((drug.selling_price * quantity for _, quantity, drug in allocations), Decimal("0.00"))
    if payment_method == Payment.Method.CASH:
        tendered = Decimal(str(cash_tendered)) if cash_tendered is not None else None
        if tendered is None or tendered < total:
            raise ValidationError({"cash_tendered": "Cash tendered must cover the sale total."})
        change = tendered - total
    else:
        tendered = None
        change = Decimal("0.00")

    sale.customer = customer
    sale.prescription = prescription
    sale.total_amount = total
    sale.save(update_fields=["customer", "prescription", "total_amount", "updated_at"])
    for batch, quantity, drug in allocations:
        batch.available_quantity -= quantity
        batch.save(update_fields=["available_quantity", "updated_at"])
        line_total = drug.selling_price * quantity
        SaleItem.objects.create(sale=sale, batch=batch, quantity=quantity, unit_price=drug.selling_price, line_total=line_total)
        StockMovement.objects.create(
            batch=batch, quantity_delta=-quantity, reason=StockMovement.Reason.SALE,
            reference=sale.sale_number, performed_by=actor,
        )
    Payment.objects.create(
        sale=sale, method=payment_method, amount=total, cash_tendered=tendered,
        change_given=change, reference=payment_reference, recorded_by=actor,
    )
    sale.status = Sale.Status.COMPLETED
    sale.completed_at = timezone.now()
    sale.save(update_fields=["status", "completed_at", "updated_at"])
    AuditLog.objects.create(actor=actor, action="sale.completed", entity_type="Sale", entity_id=str(sale.pk), metadata={"sale_number": sale.sale_number, "total": str(total)})
    return sale


@transaction.atomic
def receive_purchase_order(*, actor, purchase_order_id, request_key, items):
    existing = GoodsReceipt.objects.filter(request_key=request_key).first()
    if existing:
        return existing
    if not request_key or not items:
        raise ValidationError({"receipt": "A unique request key and at least one receipt item are required."})
    order = PurchaseOrder.objects.select_for_update().filter(pk=purchase_order_id).first()
    if not order or order.status not in (PurchaseOrder.Status.ORDERED, PurchaseOrder.Status.PARTIAL):
        raise ValidationError({"purchase_order": "Only an ordered, open purchase order can receive goods."})

    receipt = GoodsReceipt.objects.create(
        receipt_number=f"R-{uuid4().hex[:20].upper()}",
        purchase_order=order, received_by=actor, request_key=request_key,
    )
    received_by_item = defaultdict(int)
    for item in items:
        received_by_item[int(item["purchase_order_item_id"])] += int(item["quantity"])

    po_items = {
        item.id: item for item in PurchaseOrderItem.objects.select_for_update()
        .filter(purchase_order=order, id__in=received_by_item).order_by("id")
    }
    if len(po_items) != len(received_by_item):
        raise ValidationError({"items": "A receipt line does not belong to this purchase order."})
    for item_id, quantity in received_by_item.items():
        if quantity < 1:
            raise ValidationError({"items": "Received quantities must be positive."})
        po_item = po_items[item_id]
        previously_received = GoodsReceiptItem.objects.filter(purchase_order_item=po_item).aggregate(
            total=Sum("received_quantity")
        )["total"] or 0
        if previously_received + quantity > po_item.ordered_quantity:
            raise ValidationError({"items": f"Receipt exceeds the outstanding quantity for {po_item.drug.generic_name}."})

    for item in items:
        po_item = po_items[int(item["purchase_order_item_id"])]
        quantity = int(item["quantity"])
        batch_number = str(item["batch_number"]).strip()
        expiry_date = date.fromisoformat(item["expiry_date"])
        if expiry_date < timezone.now().astimezone(ZoneInfo(settings.BUSINESS_TIME_ZONE)).date():
            raise ValidationError({"expiry_date": "An already-expired batch cannot be received as sellable stock."})
        batch, created = Batch.objects.select_for_update().get_or_create(
            drug=po_item.drug, batch_number=batch_number,
            defaults={"supplier": order.supplier, "expiry_date": expiry_date, "received_quantity": quantity, "available_quantity": quantity},
        )
        if not created:
            if batch.supplier_id != order.supplier_id or batch.expiry_date != expiry_date or batch.status != Batch.Status.AVAILABLE:
                raise ValidationError({"batch_number": "Existing batch details differ; quarantine or investigate instead of merging."})
            batch.received_quantity += quantity
            batch.available_quantity += quantity
            batch.save(update_fields=["received_quantity", "available_quantity", "updated_at"])
        GoodsReceiptItem.objects.create(receipt=receipt, purchase_order_item=po_item, batch=batch, received_quantity=quantity)
        StockMovement.objects.create(batch=batch, quantity_delta=quantity, reason=StockMovement.Reason.RECEIPT, reference=receipt.receipt_number, performed_by=actor)

    all_order_items = list(PurchaseOrderItem.objects.filter(purchase_order=order))
    all_received = all(
        (GoodsReceiptItem.objects.filter(purchase_order_item=line).aggregate(total=Sum("received_quantity"))["total"] or 0) >= line.ordered_quantity
        for line in all_order_items
    )
    order.status = PurchaseOrder.Status.RECEIVED if all_received else PurchaseOrder.Status.PARTIAL
    order.save(update_fields=["status", "updated_at"])
    AuditLog.objects.create(actor=actor, action="goods_receipt.created", entity_type="GoodsReceipt", entity_id=str(receipt.pk), metadata={"receipt_number": receipt.receipt_number})
    return receipt


@transaction.atomic
def adjust_batch_stock(*, actor: Staff, batch_id: int, quantity_delta: int, reason: str):
    if quantity_delta == 0:
        raise ValidationError({"quantity_delta": "Adjustment must change the balance."})
    reason = reason.strip()
    if len(reason) < 8:
        raise ValidationError({"reason": "Provide a meaningful reason of at least 8 characters."})
    batch = Batch.objects.select_for_update().filter(pk=batch_id).first()
    if not batch:
        raise ValidationError({"batch": "Batch not found."})
    new_balance = batch.available_quantity + quantity_delta
    if new_balance < 0:
        raise ValidationError({"quantity_delta": "Stock cannot be adjusted below zero."})
    if new_balance > batch.received_quantity:
        raise ValidationError({"quantity_delta": "Adjustment cannot exceed documented received quantity."})
    batch.available_quantity = new_balance
    batch.save(update_fields=["available_quantity", "updated_at"])
    movement = StockMovement.objects.create(
        batch=batch, quantity_delta=quantity_delta, reason=StockMovement.Reason.ADJUSTMENT,
        note=reason, performed_by=actor,
    )
    AuditLog.objects.create(
        actor=actor, action="stock.adjusted", entity_type="Batch", entity_id=str(batch.pk),
        metadata={"movement_id": movement.pk, "quantity_delta": quantity_delta, "reason": reason},
    )
    return movement
