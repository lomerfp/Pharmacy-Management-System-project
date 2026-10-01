from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from .models import Batch, Category, Customer, Doctor, Drug, Prescription, PrescriptionItem, PurchaseOrder, PurchaseOrderItem, Role, Sale, Staff, Supplier
from .models import PharmacySetting


class HealthSerializer(serializers.Serializer):
    status = serializers.CharField()
    service = serializers.CharField()


class StockAdjustmentSerializer(serializers.Serializer):
    quantity_delta = serializers.IntegerField()
    reason = serializers.CharField(max_length=255, min_length=8)


class PharmacySettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PharmacySetting
        fields = ("key", "value", "updated_at")
        read_only_fields = ("updated_at",)


class PharmacySettingsInputSerializer(serializers.Serializer):
    pharmacy_name = serializers.CharField(max_length=160, required=False)
    logo_path = serializers.CharField(max_length=255, required=False, allow_blank=True)
    address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=40, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    receipt_footer = serializers.CharField(max_length=500, required=False, allow_blank=True)
    currency = serializers.ChoiceField(choices=("UGX", "USD", "KES", "TZS"), required=False)
    timezone = serializers.CharField(max_length=80, required=False)
    expiry_warning_days = serializers.IntegerField(min_value=1, max_value=365, required=False)


class PharmacySettingsResponseSerializer(serializers.Serializer):
    key = serializers.CharField()
    value = serializers.JSONField()
    updated_at = serializers.DateTimeField()


class ReportResponseSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    previous = serializers.CharField(allow_null=True)
    results = serializers.ListField(child=serializers.DictField())


class CurrentStaffSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    display_name = serializers.CharField()
    role = serializers.CharField(allow_null=True)
    permissions = serializers.ListField(child=serializers.CharField())


class DetailResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class PasswordChangeInputSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])


class PasswordResetRequestInputSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmInputSerializer(serializers.Serializer):
    token = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])


class LogoutInputSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ("id", "name", "description", "permissions", "is_active", "created_at", "updated_at")
        read_only_fields = ("created_at", "updated_at")


class StaffSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, validators=[validate_password])

    class Meta:
        model = Staff
        fields = ("id", "username", "email", "display_name", "role", "is_active", "password", "date_joined")
        read_only_fields = ("id", "date_joined")

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        if not password:
            raise serializers.ValidationError({"password": "A temporary password is required."})
        return Staff.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        if password:
            instance.set_password(password)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        return instance


class StaffSignupSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    display_name = serializers.CharField(max_length=160)
    password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_username(self, value):
        if Staff.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("An account with this username already exists.")
        return value

    def validate_email(self, value):
        if Staff.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        return Staff.objects.create_user(password=password, is_active=False, role=None, **validated_data)


class SignupResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ("id", "full_name", "phone", "email", "is_active", "created_at")
        read_only_fields = ("id", "created_at")


class CheckoutCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ("id", "full_name")
        read_only_fields = fields


class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = ("id", "full_name", "registration_number", "contact_phone", "is_active")


class PrescriptionItemInputSerializer(serializers.Serializer):
    drug_id = serializers.IntegerField(min_value=1)
    authorized_quantity = serializers.IntegerField(min_value=1)
    dosage = serializers.CharField(max_length=180)
    frequency = serializers.CharField(max_length=120)
    duration = serializers.CharField(max_length=120)
    instructions = serializers.CharField(required=False, allow_blank=True)


class PrescriptionCreateSerializer(serializers.Serializer):
    reference = serializers.CharField(max_length=50)
    customer_id = serializers.IntegerField(min_value=1)
    doctor_id = serializers.IntegerField(min_value=1)
    prescribed_at = serializers.DateField()
    notes = serializers.CharField(required=False, allow_blank=True)
    items = PrescriptionItemInputSerializer(many=True, allow_empty=False)

    def validate_items(self, items):
        drug_ids = [item["drug_id"] for item in items]
        if len(set(drug_ids)) != len(drug_ids):
            raise serializers.ValidationError("A drug may appear only once per prescription.")
        return items

    @transaction.atomic
    def create(self, validated_data):
        items = validated_data.pop("items")
        prescription = Prescription.objects.create(recorded_by=self.context["request"].user, **validated_data)
        PrescriptionItem.objects.bulk_create([PrescriptionItem(prescription=prescription, **item) for item in items])
        return prescription


class PrescriptionItemSerializer(serializers.ModelSerializer):
    drug_name = serializers.CharField(source="drug.generic_name", read_only=True)

    class Meta:
        model = PrescriptionItem
        fields = ("id", "drug", "drug_name", "authorized_quantity", "dosage", "frequency", "duration", "instructions")


class PrescriptionSerializer(serializers.ModelSerializer):
    items = PrescriptionItemSerializer(many=True, read_only=True)

    class Meta:
        model = Prescription
        fields = ("id", "reference", "customer", "doctor", "recorded_by", "prescribed_at", "status", "reviewed_by", "reviewed_at", "notes", "items")
        read_only_fields = fields


class PrescriptionReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=("approve", "cancel"))


class PrescriptionEligibleSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    reference = serializers.CharField()
    remaining = serializers.ListField(child=serializers.DictField())


class PurchaseOrderResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    order_number = serializers.CharField()
    status = serializers.CharField()


class PurchaseOrderTransitionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=("submit", "cancel"))


class PurchaseOrderTransitionResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    status = serializers.CharField()


class GoodsReceiptResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    receipt_number = serializers.CharField()


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")


class DrugSerializer(serializers.ModelSerializer):
    class Meta:
        model = Drug
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")


class BatchSerializer(serializers.ModelSerializer):
    drug_name = serializers.CharField(source="drug.generic_name", read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)

    class Meta:
        model = Batch
        fields = "__all__"
        read_only_fields = ("received_quantity", "available_quantity", "created_at", "updated_at")


class PurchaseOrderItemInputSerializer(serializers.Serializer):
    drug_id = serializers.IntegerField(min_value=1)
    ordered_quantity = serializers.IntegerField(min_value=1)
    unit_cost = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)


class PurchaseOrderCreateSerializer(serializers.Serializer):
    order_number = serializers.CharField(max_length=40)
    supplier_id = serializers.IntegerField(min_value=1)
    notes = serializers.CharField(required=False, allow_blank=True)
    items = PurchaseOrderItemInputSerializer(many=True, allow_empty=False)

    def validate_items(self, items):
        drug_ids = [item["drug_id"] for item in items]
        if len(set(drug_ids)) != len(drug_ids):
            raise serializers.ValidationError("A drug may appear only once per order.")
        return items


class CheckoutItemSerializer(serializers.Serializer):
    drug_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)


class CheckoutSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    prescription_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    items = CheckoutItemSerializer(many=True, allow_empty=False)
    payment_method = serializers.ChoiceField(choices=("cash", "mobile_money", "card", "bank_transfer"))
    payment_reference = serializers.CharField(max_length=120, required=False, allow_blank=True)
    cash_tendered = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0, required=False, allow_null=True)


class SaleSerializer(serializers.ModelSerializer):
    payment_method = serializers.CharField(source="payment.method", read_only=True)
    payment_amount = serializers.DecimalField(source="payment.amount", max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Sale
        fields = ("id", "sale_number", "customer", "prescription", "processed_by", "status", "completed_at", "total_amount", "payment_method", "payment_amount")


class ReceiptItemSerializer(serializers.Serializer):
    purchase_order_item_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)
    batch_number = serializers.CharField(max_length=100)
    expiry_date = serializers.DateField()


class GoodsReceiptInputSerializer(serializers.Serializer):
    items = ReceiptItemSerializer(many=True, allow_empty=False)
