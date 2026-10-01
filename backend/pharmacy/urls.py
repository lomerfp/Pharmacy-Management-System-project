from django.urls import include, path
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.routers import DefaultRouter
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from .api_views import (
    AuditHistoryView, BatchViewSet, CategoryViewSet, CheckoutCustomerLookupView, CheckoutView, CurrentStaffView, CustomerViewSet, DashboardSummaryView,
    DoctorViewSet, DrugViewSet, GoodsReceiptView, LogoutView,
    PasswordChangeView, PasswordResetConfirmView, PasswordResetRequestView,
    PharmacySettingsView, PrescriptionViewSet, PurchaseOrderCreateView,
    PurchaseOrderTransitionView, ReportView, RoleViewSet, SaleHistoryView,
    StaffSignupView, StaffViewSet, StockAdjustmentView, SupplierViewSet,
)
from .serializers import HealthSerializer


class HealthView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(responses=HealthSerializer)
    def get(self, request):
        return Response({"status": "ok", "service": "pharmacy-api"})


router = DefaultRouter()
router.register("categories", CategoryViewSet)
router.register("drugs", DrugViewSet)
router.register("suppliers", SupplierViewSet)
router.register("batches", BatchViewSet)
router.register("roles", RoleViewSet)
router.register("staff", StaffViewSet)
router.register("customers", CustomerViewSet)
router.register("doctors", DoctorViewSet)
router.register("prescriptions", PrescriptionViewSet)

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("auth/me/", CurrentStaffView.as_view(), name="current-staff"),
    path("auth/signup/", StaffSignupView.as_view(), name="staff-signup"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/password/change/", PasswordChangeView.as_view(), name="password-change"),
    path("auth/password/reset/", PasswordResetRequestView.as_view(), name="password-reset-request"),
    path("auth/password/reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("purchase-orders/", PurchaseOrderCreateView.as_view(), name="purchase-order-create"),
    path("purchase-orders/<int:pk>/transition/", PurchaseOrderTransitionView.as_view(), name="purchase-order-transition"),
    path("purchase-orders/<int:pk>/receipts/", GoodsReceiptView.as_view(), name="purchase-order-receive"),
    path("sales/checkout/", CheckoutView.as_view(), name="sale-checkout"),
    path("sales/customer-lookup/", CheckoutCustomerLookupView.as_view(), name="sale-customer-lookup"),
    path("sales/", SaleHistoryView.as_view(), name="sale-history"),
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("batches/<int:pk>/adjustments/", StockAdjustmentView.as_view(), name="batch-adjustment"),
    path("settings/", PharmacySettingsView.as_view(), name="pharmacy-settings"),
    path("audit/", AuditHistoryView.as_view(), name="audit-history"),
    path("reports/<str:report_name>/", ReportView.as_view(), name="reports"),
    path("", include(router.urls)),
]
