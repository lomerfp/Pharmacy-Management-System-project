from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.conf import settings

from .models import (
    AuditLog, Batch, Category, Customer, Doctor, Drug, GoodsReceipt,
    GoodsReceiptItem, Payment, Prescription, PrescriptionItem, PurchaseOrder,
    PurchaseOrderItem, Role, Sale, SaleItem, Staff, StockMovement, Supplier,
)

if not settings.PHARMACY_LEGACY_SCHEMA:
    admin.site.register(Staff, UserAdmin)
    admin.site.register(Role)

admin.site.register((Category, Drug, Batch, Supplier, PurchaseOrder, PurchaseOrderItem, Customer, Doctor, Prescription, PrescriptionItem, Sale, SaleItem, Payment, GoodsReceipt, GoodsReceiptItem, StockMovement, AuditLog))
