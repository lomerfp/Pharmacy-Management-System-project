from django.db import transaction
import hashlib
import secrets
from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken

from .models import AuditLog, Batch, Category, Customer, Doctor, Drug, PasswordResetToken, PharmacySetting, Prescription, PurchaseOrder, PurchaseOrderItem, Role, Sale, SaleItem, Staff, StaffCredential, Supplier, set_staff_password
from .permissions import HasRolePermission
from .serializers import (
    BatchSerializer, CategorySerializer, CheckoutSerializer, DrugSerializer,
    CheckoutCustomerSerializer, CustomerSerializer, DoctorSerializer, GoodsReceiptInputSerializer, GoodsReceiptResponseSerializer, HealthSerializer,
    CurrentStaffSerializer, DetailResponseSerializer, LogoutInputSerializer,
    PasswordChangeInputSerializer, PasswordResetConfirmInputSerializer,
    PasswordResetRequestInputSerializer, SignupResponseSerializer,
    EmailTokenObtainPairSerializer, StaffSignupSerializer,
    PrescriptionCreateSerializer, PrescriptionEligibleSerializer, PrescriptionReviewSerializer, PrescriptionSerializer,
    PurchaseOrderCreateSerializer, PurchaseOrderResponseSerializer,
    PurchaseOrderTransitionResponseSerializer, PurchaseOrderTransitionSerializer,
    PharmacySettingsInputSerializer, PharmacySettingsResponseSerializer,
    ReportResponseSerializer, RoleSerializer,
    SaleSerializer, StaffSerializer, StockAdjustmentSerializer, SupplierSerializer,
)
from .reports import csv_file_response, movement_rows, payment_rows, purchase_rows, sales_by_drug_rows, sales_rows, stock_rows
from .services import adjust_batch_stock, complete_sale, receive_purchase_order


class EmailTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer


class RoleRestrictedModelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    permission_by_action = {
        "list": "inventory.read", "retrieve": "inventory.read",
        "create": "inventory.manage", "update": "inventory.manage",
        "partial_update": "inventory.manage", "destroy": "inventory.manage",
    }

    def get_permissions(self):
        self.required_permission = self.permission_by_action.get(self.action, "inventory.read")
        return super().get_permissions()


class CategoryViewSet(RoleRestrictedModelViewSet):
    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer
    search_fields = ("name",)
    ordering_fields = ("name", "created_at")


class DrugViewSet(RoleRestrictedModelViewSet):
    queryset = Drug.objects.select_related("category").all().order_by("generic_name", "strength")
    serializer_class = DrugSerializer
    search_fields = ("generic_name", "brand_name", "strength")
    filterset_fields = ("category", "status", "prescription_required")
    ordering_fields = ("generic_name", "selling_price", "created_at")


class SupplierViewSet(RoleRestrictedModelViewSet):
    queryset = Supplier.objects.all().order_by("name")
    serializer_class = SupplierSerializer
    permission_by_action = {**RoleRestrictedModelViewSet.permission_by_action, **{
        "list": "purchasing.read", "retrieve": "purchasing.read",
        "create": "purchasing.manage", "update": "purchasing.manage",
        "partial_update": "purchasing.manage", "destroy": "purchasing.manage",
    }}
    search_fields = ("name", "phone", "email")
    filterset_fields = ("is_active",)


class BatchViewSet(RoleRestrictedModelViewSet):
    queryset = Batch.objects.select_related("drug", "supplier").all().order_by("expiry_date", "id")
    serializer_class = BatchSerializer
    permission_by_action = {**RoleRestrictedModelViewSet.permission_by_action, **{
        "list": "inventory.read", "retrieve": "inventory.read",
        "create": "inventory.receive", "update": "inventory.quarantine",
        "partial_update": "inventory.quarantine", "destroy": "inventory.manage",
    }}
    filterset_fields = ("drug", "supplier", "status", "expiry_date")
    ordering_fields = ("expiry_date", "available_quantity")

    def perform_create(self, serializer):
        raise ValidationError("Batches are created only by the purchase receiving workflow.")

    def perform_update(self, serializer):
        raise ValidationError("Batch balances and identities cannot be edited directly.")

    def perform_destroy(self, instance):
        raise ValidationError("Historical batch records cannot be deleted.")


class PurchaseOrderCreateView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "purchasing.manage"

    @extend_schema(request=PurchaseOrderCreateSerializer, responses={201: PurchaseOrderResponseSerializer})
    def post(self, request):
        serializer = PurchaseOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with transaction.atomic():
            order = PurchaseOrder.objects.create(
                order_number=data["order_number"], supplier_id=data["supplier_id"],
                created_by=request.user, notes=data.get("notes", ""),
            )
            order.items.bulk_create([
                PurchaseOrderItem(purchase_order=order, drug_id=item["drug_id"], ordered_quantity=item["ordered_quantity"], unit_cost=item["unit_cost"])
                for item in data["items"]
            ])
        return Response({"id": order.pk, "order_number": order.order_number, "status": order.status}, status=status.HTTP_201_CREATED)


class PurchaseOrderTransitionView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "purchasing.manage"

    @transaction.atomic
    @extend_schema(request=PurchaseOrderTransitionSerializer, responses=PurchaseOrderTransitionResponseSerializer)
    def post(self, request, pk):
        order = PurchaseOrder.objects.select_for_update().filter(pk=pk).first()
        if not order:
            return Response({"detail": "Purchase order not found."}, status=404)
        if order.status != PurchaseOrder.Status.DRAFT:
            raise ValidationError("Only draft orders can be submitted or cancelled through this endpoint.")
        action = request.data.get("action")
        if action == "submit":
            if not order.items.exists():
                raise ValidationError("An order needs at least one item before submission.")
            order.status = PurchaseOrder.Status.ORDERED
            order.ordered_at = timezone.now()
        elif action == "cancel":
            order.status = PurchaseOrder.Status.CANCELLED
        else:
            raise ValidationError({"action": "Use submit or cancel."})
        order.save(update_fields=["status", "ordered_at", "updated_at"])
        return Response({"id": order.pk, "status": order.status})


class GoodsReceiptView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "purchasing.receive"

    @extend_schema(request=GoodsReceiptInputSerializer, responses={201: GoodsReceiptResponseSerializer})
    def post(self, request, pk):
        serializer = GoodsReceiptInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        receipt = receive_purchase_order(
            actor=request.user, purchase_order_id=pk,
            request_key=request.headers.get("Idempotency-Key", ""),
            items=serializer.validated_data["items"],
        )
        return Response({"id": receipt.pk, "receipt_number": receipt.receipt_number}, status=status.HTTP_201_CREATED)


class CheckoutView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "sales.checkout"

    @extend_schema(request=CheckoutSerializer, responses=SaleSerializer)
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        sale = complete_sale(
            actor=request.user, idempotency_key=request.headers.get("Idempotency-Key", ""),
            customer_id=data.get("customer_id"), prescription_id=data.get("prescription_id"),
            lines=data["items"], payment_method=data["payment_method"],
            payment_reference=data.get("payment_reference", ""), cash_tendered=data.get("cash_tendered"),
        )
        return Response(SaleSerializer(sale).data, status=status.HTTP_200_OK)


class SaleHistoryView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "sales.read"

    @extend_schema(responses=SaleSerializer(many=True))
    def get(self, request):
        sales = Sale.objects.filter(status=Sale.Status.COMPLETED).select_related("payment", "processed_by").order_by("-completed_at")[:100]
        return Response(SaleSerializer(sales, many=True).data)


class CheckoutCustomerLookupView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "sales.customer_lookup"

    @extend_schema(responses=CheckoutCustomerSerializer(many=True))
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if len(query) < 2:
            raise ValidationError({"q": "Enter at least two characters."})
        customers = Customer.objects.filter(is_active=True).filter(
            Q(full_name__icontains=query) | Q(phone__icontains=query)
        ).order_by("full_name")[:20]
        return Response(CheckoutCustomerSerializer(customers, many=True).data)


class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "dashboard.read"

    @extend_schema(responses={200: {
        "type": "object",
        "properties": {
            "business_date": {"type": "string", "format": "date"},
            "completed_sales": {"type": "integer"}, "sales_total": {"type": "string"},
            "payment_total": {"type": "string"}, "active_drug_count": {"type": "integer"},
            "sellable_units": {"type": "integer"}, "low_stock_drugs": {"type": "array", "items": {"type": "object"}},
            "expired_batch_count": {"type": "integer"}, "expiring_batch_count": {"type": "integer"},
            "pending_purchase_orders": {"type": "integer"}, "top_selling_drugs": {"type": "array", "items": {"type": "object"}},
            "recent_activity": {"type": "array", "items": {"type": "object"}},
        },
    }})
    def get(self, request):
        business_tz = ZoneInfo(settings.BUSINESS_TIME_ZONE)
        business_date = timezone.now().astimezone(business_tz).date()
        start_local = datetime.combine(business_date, time.min, tzinfo=business_tz)
        end_local = datetime.combine(business_date + timedelta(days=1), time.min, tzinfo=business_tz)
        start_utc = start_local.astimezone(ZoneInfo("UTC"))
        end_utc = end_local.astimezone(ZoneInfo("UTC"))

        todays_sales = Sale.objects.filter(status=Sale.Status.COMPLETED, completed_at__gte=start_utc, completed_at__lt=end_utc)
        sale_totals = todays_sales.aggregate(count=Count("id"), total=Sum("total_amount"), payments=Sum("payment__amount"))
        sellable_filter = Q(batches__status=Batch.Status.AVAILABLE, batches__expiry_date__gte=business_date, batches__drug__status=Drug.Status.ACTIVE)
        drug_rows = Drug.objects.filter(status=Drug.Status.ACTIVE).annotate(
            sellable=Sum("batches__available_quantity", filter=sellable_filter),
        ).values("id", "generic_name", "strength", "reorder_level", "sellable")
        low_stock = [{
            "drug_id": row["id"], "name": row["generic_name"], "strength": row["strength"],
            "available_units": row["sellable"] or 0, "reorder_level": row["reorder_level"],
        } for row in drug_rows if (row["sellable"] or 0) <= row["reorder_level"]]
        sellable_units = sum(row["sellable"] or 0 for row in drug_rows)
        batch_base = Batch.objects.filter(available_quantity__gt=0)
        expiring_limit = business_date + timedelta(days=settings.EXPIRY_WARNING_DAYS)
        top_selling = SaleItem.objects.filter(sale__in=todays_sales).values(
            "batch__drug_id", "batch__drug__generic_name",
        ).annotate(units=Sum("quantity")).order_by("-units")[:5]
        activity = AuditLog.objects.select_related("actor").order_by("-occurred_at").values(
            "action", "entity_type", "entity_id", "occurred_at",
        )[:8]
        return Response({
            "business_date": business_date.isoformat(),
            "completed_sales": sale_totals["count"] or 0,
            "sales_total": f"{sale_totals['total'] or Decimal('0.00'):.2f}",
            "payment_total": f"{sale_totals['payments'] or Decimal('0.00'):.2f}",
            "active_drug_count": Drug.objects.filter(status=Drug.Status.ACTIVE).count(),
            "sellable_units": sellable_units,
            "low_stock_drugs": low_stock,
            "expired_batch_count": batch_base.filter(expiry_date__lt=business_date).count(),
            "expiring_batch_count": batch_base.filter(expiry_date__gte=business_date, expiry_date__lte=expiring_limit, status=Batch.Status.AVAILABLE).count(),
            "pending_purchase_orders": PurchaseOrder.objects.filter(status__in=[PurchaseOrder.Status.ORDERED, PurchaseOrder.Status.PARTIAL]).count(),
            "top_selling_drugs": [{"drug_id": item["batch__drug_id"], "name": item["batch__drug__generic_name"], "units": item["units"]} for item in top_selling],
            "recent_activity": list(activity),
        })


class StockAdjustmentView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "inventory.adjust"

    @extend_schema(request=StockAdjustmentSerializer, responses={201: ReportResponseSerializer})
    def post(self, request, pk):
        serializer = StockAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        movement = adjust_batch_stock(actor=request.user, batch_id=pk, **serializer.validated_data)
        return Response({"id": movement.pk, "batch_id": movement.batch_id, "quantity_delta": movement.quantity_delta, "reason": movement.note}, status=201)


class PharmacySettingsView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "settings.manage"
    allowed_keys = {"pharmacy_name", "logo_path", "address", "phone", "email", "receipt_footer", "currency", "timezone", "expiry_warning_days"}

    @extend_schema(responses=PharmacySettingsResponseSerializer(many=True))
    def get(self, request):
        values = list(PharmacySetting.objects.order_by("key").values("key", "value", "updated_at"))
        return Response(values)

    @extend_schema(request=PharmacySettingsInputSerializer, responses=PharmacySettingsResponseSerializer(many=True))
    def patch(self, request):
        if not isinstance(request.data, dict) or not request.data:
            raise ValidationError({"settings": "Provide one or more key/value settings."})
        unsupported = set(request.data) - self.allowed_keys
        if unsupported:
            raise ValidationError({"settings": f"Unsupported setting keys: {', '.join(sorted(unsupported))}."})
        validated = PharmacySettingsInputSerializer(data=request.data)
        validated.is_valid(raise_exception=True)
        with transaction.atomic():
            for key, value in validated.validated_data.items():
                if key == "timezone":
                    try:
                        ZoneInfo(value)
                    except Exception as exc:
                        raise ValidationError({"timezone": "Use a valid IANA timezone such as Africa/Kampala."}) from exc
                setting, _ = PharmacySetting.objects.select_for_update().get_or_create(key=key, defaults={"value": value})
                setting.value = value
                setting.save(update_fields=["value", "updated_at"])
                AuditLog.objects.create(actor=request.user, action="settings.updated", entity_type="PharmacySetting", entity_id=key, metadata={"key": key})
        return self.get(request)


class ReportView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "reports.read"
    pagination_class = PageNumberPagination
    report_builders = {
        "stock": lambda request: stock_rows(batch=False),
        "batches": lambda request: stock_rows(batch=True),
        "sales": sales_rows,
        "sales-by-drug": sales_by_drug_rows,
        "payments": payment_rows,
        "purchases": lambda request: purchase_rows(),
        "movements": movement_rows,
    }

    @extend_schema(responses=ReportResponseSerializer)
    def get(self, request, report_name):
        builder = self.report_builders.get(report_name)
        if builder is None:
            raise ValidationError({"report": "Unknown report."})
        rows = builder(request)
        if request.query_params.get("export", "").lower() == "csv":
            return csv_file_response(rows, report_name)
        paginator = self.pagination_class()
        paginator.page_size = 50
        paginator.page_query_param = "page"
        paginator.request = request
        paginator.paginate_queryset(rows, request, view=self)
        return paginator.get_paginated_response(paginator.page.object_list)


class AuditHistoryView(APIView):
    permission_classes = [IsAuthenticated, HasRolePermission]
    required_permission = "audit.read"

    @extend_schema(responses=ReportResponseSerializer)
    def get(self, request):
        records = AuditLog.objects.order_by("-occurred_at").values(
            "id", "actor_id", "action", "entity_type", "entity_id", "metadata", "occurred_at",
        )[:500]
        paginator = PageNumberPagination()
        paginator.page_size = 50
        paginator.paginate_queryset(records, request, view=self)
        return paginator.get_paginated_response(paginator.page.object_list)


class PermissionRestrictedViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasRolePermission]
    permission_by_action = {}

    def get_permissions(self):
        self.required_permission = self.permission_by_action.get(self.action, "permission.unassigned")
        return super().get_permissions()


class RoleViewSet(PermissionRestrictedViewSet):
    queryset = Role.objects.all().order_by("name")
    serializer_class = RoleSerializer
    permission_by_action = {action: "staff.manage" for action in ("list", "retrieve", "create", "update", "partial_update", "destroy")}
    if settings.PHARMACY_LEGACY_SCHEMA:
        http_method_names = ["get", "head", "options"]

    def perform_destroy(self, instance):
        raise ValidationError("Roles cannot be deleted; deactivate them to preserve history.")


class StaffViewSet(PermissionRestrictedViewSet):
    queryset = Staff.objects.select_related("role").all().order_by("display_name")
    serializer_class = StaffSerializer
    permission_by_action = {action: "staff.manage" for action in ("list", "retrieve", "create", "update", "partial_update", "destroy")}
    search_fields = ("display_name", "email") if settings.PHARMACY_LEGACY_SCHEMA else ("username", "display_name", "email")
    filterset_fields = ("role", "is_active")
    if settings.PHARMACY_LEGACY_SCHEMA:
        http_method_names = ["get", "head", "options"]

    def perform_destroy(self, instance):
        if instance.pk == self.request.user.pk:
            raise ValidationError("You cannot remove your own staff account.")
        if instance.is_active and instance.role and "staff.manage" in instance.role.permissions:
            other_active_admins = Staff.objects.filter(is_active=True, role__is_active=True).exclude(pk=instance.pk)
            if not any("staff.manage" in admin.role.permissions for admin in other_active_admins if admin.role):
                raise ValidationError("The last active staff administrator cannot be removed.")
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])
        AuditLog.objects.create(
            actor=self.request.user, action="staff.deactivated", entity_type="Staff",
            entity_id=str(instance.pk), metadata={"username": instance.username},
        )


class CustomerViewSet(PermissionRestrictedViewSet):
    queryset = Customer.objects.all().order_by("full_name")
    serializer_class = CustomerSerializer
    permission_by_action = {
        "list": "clinical.read", "retrieve": "clinical.read",
        "create": "clinical.manage", "update": "clinical.manage",
        "partial_update": "clinical.manage", "destroy": "clinical.manage",
    }
    search_fields = ("full_name", "phone")
    filterset_fields = ("is_active",)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])


class DoctorViewSet(PermissionRestrictedViewSet):
    queryset = Doctor.objects.all().order_by("full_name")
    serializer_class = DoctorSerializer
    permission_by_action = {
        "list": "prescriptions.read", "retrieve": "prescriptions.read",
        "create": "prescriptions.manage", "update": "prescriptions.manage",
        "partial_update": "prescriptions.manage", "destroy": "prescriptions.manage",
    }
    search_fields = ("full_name", "registration_number")
    filterset_fields = ("is_active",)

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])


class PrescriptionViewSet(PermissionRestrictedViewSet):
    queryset = Prescription.objects.select_related("customer", "doctor", "recorded_by", "reviewed_by").prefetch_related("items__drug").all().order_by("-prescribed_at", "-id")
    serializer_class = PrescriptionSerializer
    permission_by_action = {
        "list": "prescriptions.read", "retrieve": "prescriptions.read",
        "create": "prescriptions.manage", "review": "prescriptions.review",
        "eligible": "sales.checkout",
    }
    filterset_fields = ("status", "customer", "doctor")
    search_fields = ("reference", "customer__full_name", "doctor__full_name")

    def get_serializer_class(self):
        if self.action == "create":
            return PrescriptionCreateSerializer
        if self.action == "review":
            return PrescriptionReviewSerializer
        return self.serializer_class

    @transaction.atomic
    def perform_create(self, serializer):
        prescription = serializer.save()
        AuditLog.objects.create(actor=self.request.user, action="prescription.recorded", entity_type="Prescription", entity_id=str(prescription.pk), metadata={"reference": prescription.reference})

    @action(methods=["post"], detail=True)
    @transaction.atomic
    def review(self, request, pk=None):
        prescription = Prescription.objects.select_for_update().filter(pk=pk).first()
        if not prescription:
            return Response({"detail": "Prescription not found."}, status=404)
        if prescription.status != Prescription.Status.PENDING_REVIEW:
            raise ValidationError("Only pending prescriptions may be reviewed.")
        serializer = PrescriptionReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prescription.status = Prescription.Status.APPROVED if serializer.validated_data["action"] == "approve" else Prescription.Status.CANCELLED
        prescription.reviewed_by = request.user
        prescription.reviewed_at = timezone.now()
        prescription.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
        AuditLog.objects.create(actor=request.user, action=f"prescription.{prescription.status}", entity_type="Prescription", entity_id=str(prescription.pk), metadata={"reference": prescription.reference})
        return Response(PrescriptionSerializer(prescription).data)

    @action(methods=["get"], detail=False)
    def eligible(self, request):
        customer_id = request.query_params.get("customer_id")
        if not customer_id:
            raise ValidationError({"customer_id": "This value is required."})
        prescriptions = self.get_queryset().filter(customer_id=customer_id, status=Prescription.Status.APPROVED)
        result = []
        for prescription in prescriptions:
            remaining = []
            for item in prescription.items.all():
                dispensed = SaleItem.objects.filter(sale__prescription=prescription, sale__status=Sale.Status.COMPLETED, batch__drug_id=item.drug_id).aggregate(total=Sum("quantity"))["total"] or 0
                if item.authorized_quantity > dispensed:
                    remaining.append({"drug_id": item.drug_id, "drug_name": item.drug.generic_name, "remaining_quantity": item.authorized_quantity - dispensed})
            result.append({"id": prescription.id, "reference": prescription.reference, "remaining": remaining})
        return Response(PrescriptionEligibleSerializer(result, many=True).data)


class CurrentStaffView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=CurrentStaffSerializer)
    def get(self, request):
        user = request.user
        return Response({"id": user.id, "username": user.username, "display_name": user.display_name, "role": user.role.name if user.role else None, "permissions": user.role.permissions if user.role and user.role.is_active else []})


class StaffSignupView(APIView):
    permission_classes = []

    @extend_schema(request=StaffSignupSerializer, responses={201: SignupResponseSerializer})
    def post(self, request):
        if settings.PHARMACY_LEGACY_SCHEMA:
            return Response({"detail": "Staff accounts are provisioned from the existing legacy staff table."}, status=409)
        serializer = StaffSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        staff = serializer.save()
        AuditLog.objects.create(
            actor=None, action="staff.signup_requested", entity_type="Staff",
            entity_id=str(staff.pk), metadata={"username": staff.username},
        )
        return Response(
            {"detail": "Account request received. An administrator must assign a role and activate access."},
            status=status.HTTP_201_CREATED,
        )


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=PasswordChangeInputSerializer, responses=DetailResponseSerializer)
    def post(self, request):
        old_password = request.data.get("old_password", "")
        new_password = request.data.get("new_password", "")
        if not request.user.check_password(old_password):
            raise ValidationError({"old_password": "Current password is incorrect."})
        validate_password(new_password, request.user)
        set_staff_password(request.user, new_password)
        for token in OutstandingToken.objects.filter(user=request.user):
            BlacklistedToken.objects.get_or_create(token=token)
        if not settings.PHARMACY_LEGACY_SCHEMA:
            AuditLog.objects.create(actor=request.user, action="staff.password_changed", entity_type="Staff", entity_id=str(request.user.pk), metadata={})
        return Response({"detail": "Password changed. Sign in again with the new password."})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=LogoutInputSerializer, responses={204: None})
    def post(self, request):
        token = request.data.get("refresh", "")
        if not token:
            raise ValidationError({"refresh": "Refresh token is required."})
        try:
            RefreshToken(token).blacklist()
        except Exception as exc:
            raise ValidationError({"refresh": "Refresh token is invalid or already revoked."}) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetRequestView(APIView):
    permission_classes = []

    @extend_schema(request=PasswordResetRequestInputSerializer, responses=DetailResponseSerializer)
    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        credential = StaffCredential.objects.select_related("staff").filter(
            email__iexact=email, staff__email__iexact=email, staff__is_active=True,
        ).first() if email else None
        if credential:
            staff = credential.staff
            raw_token = secrets.token_urlsafe(32)
            PasswordResetToken.objects.create(
                staff=staff, token_digest=hashlib.sha256(raw_token.encode()).hexdigest(),
                expires_at=timezone.now() + timedelta(minutes=30),
            )
            send_mail("Pharmacy password reset", f"Single-use reset code: {raw_token}", settings.DEFAULT_FROM_EMAIL, [credential.email], fail_silently=True)
        return Response({"detail": "If an active account matches that address, reset instructions have been sent."})


class PasswordResetConfirmView(APIView):
    permission_classes = []

    @transaction.atomic
    @extend_schema(request=PasswordResetConfirmInputSerializer, responses=DetailResponseSerializer)
    def post(self, request):
        token = request.data.get("token", "")
        password = request.data.get("new_password", "")
        if not token:
            raise ValidationError({"token": "Reset token is required."})
        token_digest = hashlib.sha256(token.encode()).hexdigest()
        reset = PasswordResetToken.objects.select_for_update().select_related("staff").filter(token_digest=token_digest, consumed_at__isnull=True, expires_at__gt=timezone.now(), staff__is_active=True).first()
        if not reset:
            raise ValidationError({"token": "Reset token is invalid or expired."})
        validate_password(password, reset.staff)
        set_staff_password(reset.staff, password)
        reset.consumed_at = timezone.now()
        reset.save(update_fields=["consumed_at"])
        if not settings.PHARMACY_LEGACY_SCHEMA:
            AuditLog.objects.create(actor=reset.staff, action="staff.password_reset", entity_type="Staff", entity_id=str(reset.staff_id), metadata={})
        return Response({"detail": "Password reset successfully. Please sign in."})
