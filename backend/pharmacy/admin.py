from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    AuditLog, Batch, Category, Customer, Doctor, Drug, GoodsReceipt,
    GoodsReceiptItem, Payment, Prescription, PrescriptionItem, PurchaseOrder,
    PurchaseOrderItem, Role, Sale, SaleItem, Staff, StockMovement, Supplier,
)

admin.site.register(Staff, UserAdmin)
admin.site.register((Role, Category, Drug, Batch, Supplier, PurchaseOrder, PurchaseOrderItem, Customer, Doctor, Prescription, PrescriptionItem, Sale, SaleItem, Payment, GoodsReceipt, GoodsReceiptItem, StockMovement, AuditLog))
