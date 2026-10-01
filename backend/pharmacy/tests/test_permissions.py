from django.test import RequestFactory, TestCase
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView
from rest_framework.response import Response

from pharmacy.models import Role, Staff
from pharmacy.permissions import HasRolePermission


class PermissionView(APIView):
    permission_classes = [HasRolePermission]
    required_permission = "inventory.manage"

    def get(self, request):
        return Response({"ok": True})


class RolePermissionTests(TestCase):
    def test_role_permission_is_required(self):
        role = Role.objects.create(name="Read only", permissions=["inventory.read"])
        user = Staff.objects.create_user(username="viewer", password="test-password-12345", display_name="Demo Viewer", role=role)
        request = APIRequestFactory().get("/api/test/")
        force_authenticate(request, user=user)

        response = PermissionView.as_view()(request)

        self.assertEqual(response.status_code, 403)

    def test_assigned_permission_allows_request(self):
        role = Role.objects.create(name="Inventory Officer", permissions=["inventory.manage"])
        user = Staff.objects.create_user(username="officer", password="test-password-12345", display_name="Demo Officer", role=role)
        request = APIRequestFactory().get("/api/test/")
        force_authenticate(request, user=user)

        response = PermissionView.as_view()(request)

        self.assertEqual(response.status_code, 200)
