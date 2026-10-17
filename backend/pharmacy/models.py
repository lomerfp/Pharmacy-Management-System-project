from django.conf import settings
from django.contrib.auth.hashers import check_password as check_encoded_password, make_password
from django.contrib.auth.models import AbstractUser, UserManager
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Q


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


if settings.PHARMACY_LEGACY_SCHEMA:
    from .legacy_auth_models import Role, Staff
else:
    class Role(TimestampedModel):
        name = models.CharField(max_length=80, unique=True)
        description = models.CharField(max_length=255, blank=True)
        permissions = models.JSONField(default=list)
        is_active = models.BooleanField(default=True)

        def __str__(self):
            return self.name


    class StaffManager(UserManager):
        use_in_migrations = False

        def _create_user(self, username, email, password, **extra_fields):
            email = self.normalize_email(email)
            staff = self.model(username=username, email=email, **extra_fields)
            staff.set_unusable_password()
            staff.save(using=self._db)
            if password:
                staff.set_password(password)
                staff.save(using=self._db, update_fields=["password"])
            return staff


    class Staff(AbstractUser, TimestampedModel):
        REQUIRED_FIELDS = ["display_name"]
        objects = StaffManager()

        role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="staff_members", null=True, blank=True)
        display_name = models.CharField(max_length=160, blank=True)
        is_active = models.BooleanField(default=True)

        def set_password(self, raw_password):
            self.password = make_password(None)
            self._pending_credential_password = raw_password

        def check_password(self, raw_password):
            credential = StaffCredential.objects.filter(staff_id=self.pk).first()
            return bool(credential and check_encoded_password(raw_password, credential.password_hash))

        @transaction.atomic
        def save(self, *args, **kwargs):
            pending_password = getattr(self, "_pending_credential_password", ...)
            result = super().save(*args, **kwargs)
            credential = StaffCredential.objects.filter(staff_id=self.pk).first()
            if pending_password is not ...:
                del self._pending_credential_password
                if pending_password and self.email.strip():
                    StaffCredential.objects.update_or_create(
                        staff=self,
                        defaults={
                            "email": self.email.strip().casefold(),
                            "password_hash": make_password(pending_password),
                        },
                    )
            elif credential:
                email = self.email.strip().casefold()
                if email and credential.email != email:
                    credential.email = email
                    credential.save(update_fields=["email", "updated_at"])
            return result

        def __str__(self):
            return self.display_name or self.username


class StaffCredential(models.Model):
    staff = models.OneToOneField(
        Staff, on_delete=models.CASCADE, related_name="credential", db_column="StaffID"
    )
    email = models.EmailField(max_length=254, unique=True)
    password_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "staff_credentials"


def set_staff_password(staff, raw_password):
    staff.set_password(raw_password)
    if not settings.PHARMACY_LEGACY_SCHEMA:
        staff.save(update_fields=["password"])


class Category(TimestampedModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Drug(TimestampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"

    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="drugs")
    generic_name = models.CharField(max_length=180)
    brand_name = models.CharField(max_length=180, blank=True)
    strength = models.CharField(max_length=100)
    dosage_form = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    unit_of_measure = models.CharField(max_length=40)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    reorder_level = models.PositiveIntegerField(default=0)
    prescription_required = models.BooleanField(default=False)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE, db_index=True)

    class Meta:
        indexes = [models.Index(fields=["generic_name", "brand_name"])]

    def __str__(self):
        return f"{self.generic_name} {self.strength}"


class Supplier(TimestampedModel):
    name = models.CharField(max_length=180, unique=True)
    contact_name = models.CharField(max_length=160, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Batch(TimestampedModel):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        QUARANTINED = "quarantined", "Quarantined"
        INACTIVE = "inactive", "Inactive"

    drug = models.ForeignKey(Drug, on_delete=models.PROTECT, related_name="batches")
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="batches")
    batch_number = models.CharField(max_length=100)
    expiry_date = models.DateField(db_index=True)
    received_quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    available_quantity = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.AVAILABLE, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["drug", "batch_number"], name="uq_batch_drug_number"),
            models.CheckConstraint(condition=Q(available_quantity__lte=models.F("received_quantity")), name="ck_batch_available_lte_received"),
        ]
        indexes = [models.Index(fields=["drug", "status", "expiry_date", "id"], name="ix_batch_fefo")]

    def __str__(self):
        return f"{self.drug} / {self.batch_number}"


class PurchaseOrder(TimestampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ORDERED = "ordered", "Ordered"
        PARTIAL = "partially_received", "Partially received"
        RECEIVED = "received", "Received"
        CANCELLED = "cancelled", "Cancelled"

    order_number = models.CharField(max_length=40, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchase_orders")
    created_by = models.ForeignKey(Staff, on_delete=models.PROTECT, related_name="purchase_orders")
    ordered_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT, db_index=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.order_number


class PurchaseOrderItem(TimestampedModel):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name="items")
    drug = models.ForeignKey(Drug, on_delete=models.PROTECT, related_name="purchase_order_items")
    ordered_quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])

    class Meta:
        constraints = [models.UniqueConstraint(fields=["purchase_order", "drug"], name="uq_po_item_drug")]


class Customer(TimestampedModel):
    full_name = models.CharField(max_length=180)
    phone = models.CharField(max_length=40, blank=True, db_index=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.full_name


class Doctor(TimestampedModel):
    full_name = models.CharField(max_length=180)
    registration_number = models.CharField(max_length=100, blank=True, unique=True)
    contact_phone = models.CharField(max_length=40, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.full_name


class Prescription(TimestampedModel):
    class Status(models.TextChoices):
        PENDING_REVIEW = "pending_review", "Pending review"
        APPROVED = "approved", "Approved"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    reference = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="prescriptions")
    doctor = models.ForeignKey(Doctor, on_delete=models.PROTECT, related_name="prescriptions")
    recorded_by = models.ForeignKey(Staff, on_delete=models.PROTECT, related_name="prescriptions_recorded")
    prescribed_at = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_REVIEW, db_index=True)
    reviewed_by = models.ForeignKey(Staff, on_delete=models.PROTECT, related_name="prescriptions_reviewed", null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.reference


class PrescriptionItem(TimestampedModel):
    prescription = models.ForeignKey(Prescription, on_delete=models.PROTECT, related_name="items")
    drug = models.ForeignKey(Drug, on_delete=models.PROTECT, related_name="prescription_items")
    authorized_quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    dosage = models.CharField(max_length=180)
    frequency = models.CharField(max_length=120)
    duration = models.CharField(max_length=120)
    instructions = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["prescription", "drug"], name="uq_prescription_item_drug")]


class Sale(TimestampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    sale_number = models.CharField(max_length=40, unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="sales", null=True, blank=True)
    prescription = models.ForeignKey(Prescription, on_delete=models.PROTECT, related_name="sales", null=True, blank=True)
    processed_by = models.ForeignKey(Staff, on_delete=models.PROTECT, related_name="sales")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    idempotency_key = models.CharField(max_length=100, unique=True, null=True, blank=True)

    def __str__(self):
        return self.sale_number


class SaleItem(TimestampedModel):
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name="items")
    batch = models.ForeignKey(Batch, on_delete=models.PROTECT, related_name="sale_items")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    line_total = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])

    class Meta:
        indexes = [models.Index(fields=["sale", "batch"])]


class Payment(TimestampedModel):
    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        MOBILE_MONEY = "mobile_money", "Mobile Money"
        CARD = "card", "Card"
        BANK_TRANSFER = "bank_transfer", "Bank Transfer"

    sale = models.OneToOneField(Sale, on_delete=models.PROTECT, related_name="payment")
    method = models.CharField(max_length=20, choices=Method.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(0)])
    cash_tendered = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    change_given = models.DecimalField(max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    reference = models.CharField(max_length=120, blank=True)
    recorded_by = models.ForeignKey(Staff, on_delete=models.PROTECT, related_name="payments_recorded")
    recorded_at = models.DateTimeField(auto_now_add=True)


# Implementation extensions: provenance, stock auditability, and sensitive-action accountability.
class GoodsReceipt(TimestampedModel):
    receipt_number = models.CharField(max_length=50, unique=True)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name="receipts")
    received_by = models.ForeignKey(Staff, on_delete=models.PROTECT, related_name="goods_receipts")
    received_at = models.DateTimeField(auto_now_add=True)
    request_key = models.CharField(max_length=100, unique=True)
    supplier_delivery_reference = models.CharField(max_length=120, blank=True)


class GoodsReceiptItem(TimestampedModel):
    receipt = models.ForeignKey(GoodsReceipt, on_delete=models.PROTECT, related_name="items")
    purchase_order_item = models.ForeignKey(PurchaseOrderItem, on_delete=models.PROTECT, related_name="receipt_items")
    batch = models.ForeignKey(Batch, on_delete=models.PROTECT, related_name="receipt_items")
    received_quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])


class StockMovement(TimestampedModel):
    class Reason(models.TextChoices):
        RECEIPT = "receipt", "Goods receipt"
        SALE = "sale", "Sale"
        ADJUSTMENT = "adjustment", "Adjustment"
        QUARANTINE = "quarantine", "Quarantine"
        REVERSAL = "reversal", "Audited reversal"

    batch = models.ForeignKey(Batch, on_delete=models.PROTECT, related_name="stock_movements")
    quantity_delta = models.IntegerField()
    reason = models.CharField(max_length=16, choices=Reason.choices)
    reference = models.CharField(max_length=100, blank=True)
    note = models.CharField(max_length=255, blank=True)
    performed_by = models.ForeignKey(Staff, on_delete=models.PROTECT, related_name="stock_movements")


class AuditLog(TimestampedModel):
    actor = models.ForeignKey(Staff, on_delete=models.PROTECT, related_name="audit_events", null=True, blank=True)
    action = models.CharField(max_length=80, db_index=True)
    entity_type = models.CharField(max_length=80)
    entity_id = models.CharField(max_length=80)
    metadata = models.JSONField(default=dict)
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)


class PasswordResetToken(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="password_reset_tokens")
    token_digest = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField(db_index=True)
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class PharmacySetting(TimestampedModel):
    key = models.CharField(max_length=80, unique=True)
    value = models.JSONField()
