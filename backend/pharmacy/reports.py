import csv
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from io import StringIO
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Batch, GoodsReceiptItem, Payment, PurchaseOrder, PurchaseOrderItem, Sale, SaleItem, StockMovement


def business_date_bounds(request):
    business_tz = ZoneInfo(settings.BUSINESS_TIME_ZONE)
    try:
        start_date = date.fromisoformat(request.query_params["start_date"]) if request.query_params.get("start_date") else timezone.now().astimezone(business_tz).date()
        end_date = date.fromisoformat(request.query_params["end_date"]) if request.query_params.get("end_date") else start_date
    except ValueError as exc:
        raise ValidationError({"date": "Dates must use ISO format YYYY-MM-DD."}) from exc
    if end_date < start_date:
        raise ValidationError({"end_date": "End date must not be before start date."})
    if (end_date - start_date).days > 366:
        raise ValidationError({"date": "A report range may not exceed 366 days."})
    start = datetime.combine(start_date, time.min, tzinfo=business_tz).astimezone(ZoneInfo("UTC"))
    end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=business_tz).astimezone(ZoneInfo("UTC"))
    return start, end


def stock_rows(*, batch=False):
    query = Batch.objects.select_related("drug", "supplier").order_by("expiry_date", "id")
    rows = []
    today = timezone.now().astimezone(ZoneInfo(settings.BUSINESS_TIME_ZONE)).date()
    for item in query:
        if batch:
            rows.append({
                "batch_id": item.id, "drug": item.drug.generic_name, "strength": item.drug.strength,
                "batch_number": item.batch_number, "supplier": item.supplier.name,
                "expiry_date": item.expiry_date.isoformat(), "received": item.received_quantity,
                "available": item.available_quantity, "status": item.status,
                "expired": item.expiry_date < today,
            })
        else:
            rows.append({
                "drug_id": item.drug_id, "drug": item.drug.generic_name, "strength": item.drug.strength,
                "batch_number": item.batch_number, "expiry_date": item.expiry_date.isoformat(),
                "available": item.available_quantity, "status": item.status,
                "sellable": item.status == Batch.Status.AVAILABLE and item.drug.status == "active" and item.expiry_date >= today,
            })
    return rows


def sales_rows(request):
    start, end = business_date_bounds(request)
    sales = Sale.objects.filter(status=Sale.Status.COMPLETED, completed_at__gte=start, completed_at__lt=end).select_related("processed_by", "payment").order_by("-completed_at")
    return [{
        "sale_number": sale.sale_number,
        "completed_at": sale.completed_at.astimezone(ZoneInfo(settings.BUSINESS_TIME_ZONE)).isoformat() if sale.completed_at else "",
        "staff": sale.processed_by.display_name,
        "total": f"{sale.total_amount:.2f}",
        "payment_method": sale.payment.method,
        "payment_total": f"{sale.payment.amount:.2f}",
        "customer_id": sale.customer_id or "",
        "prescription_id": sale.prescription_id or "",
    } for sale in sales]


def sales_by_drug_rows(request):
    start, end = business_date_bounds(request)
    values = SaleItem.objects.filter(sale__status=Sale.Status.COMPLETED, sale__completed_at__gte=start, sale__completed_at__lt=end).values(
        "batch__drug_id", "batch__drug__generic_name", "batch__drug__strength",
    ).annotate(units=Sum("quantity"), revenue=Sum("line_total")).order_by("-revenue")
    return [{"drug_id": row["batch__drug_id"], "drug": row["batch__drug__generic_name"], "strength": row["batch__drug__strength"], "units": row["units"], "revenue": f"{row['revenue'] or Decimal('0.00'):.2f}"} for row in values]


def payment_rows(request):
    start, end = business_date_bounds(request)
    values = Payment.objects.filter(sale__status=Sale.Status.COMPLETED, sale__completed_at__gte=start, sale__completed_at__lt=end).values("method").annotate(count=Sum("id"), total=Sum("amount")).order_by("method")
    return [{"method": row["method"], "count": row["count"], "total": f"{row['total'] or Decimal('0.00'):.2f}"} for row in values]


def purchase_rows():
    result = []
    orders = PurchaseOrder.objects.select_related("supplier").prefetch_related("items__drug", "items__receipt_items").order_by("-created_at")
    for order in orders:
        for item in order.items.all():
            received = sum(receipt.received_quantity for receipt in item.receipt_items.all())
            result.append({
                "order_number": order.order_number, "supplier": order.supplier.name,
                "status": order.status, "drug": item.drug.generic_name,
                "ordered": item.ordered_quantity, "received": received,
                "outstanding": max(item.ordered_quantity - received, 0),
            })
    return result


def movement_rows(request):
    start, end = business_date_bounds(request)
    query = StockMovement.objects.filter(created_at__gte=start, created_at__lt=end).select_related("batch__drug", "performed_by").order_by("-created_at")
    return [{
        "occurred_at": movement.created_at.astimezone(ZoneInfo(settings.BUSINESS_TIME_ZONE)).isoformat(),
        "drug": movement.batch.drug.generic_name, "batch_number": movement.batch.batch_number,
        "quantity_delta": movement.quantity_delta, "reason": movement.reason,
        "reference": movement.reference, "note": movement.note,
        "staff": movement.performed_by.display_name,
    } for movement in query]


def csv_file_response(rows, filename):
    from django.http import HttpResponse

    response_buffer = StringIO()
    if rows:
        writer = csv.DictWriter(response_buffer, fieldnames=list(rows[0].keys()), lineterminator="\r\n")
        writer.writeheader()
        safe_rows = []
        for row in rows:
            safe_rows.append({
                key: (f"'{value}" if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")) else value)
                for key, value in row.items()
            })
        writer.writerows(safe_rows)
    response = HttpResponse(response_buffer.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
    return response
