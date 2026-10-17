from unittest import skipUnless

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import connection
from django.test import TestCase
from rest_framework.test import APIClient

from pharmacy.models import Role, Staff, StaffCredential, set_staff_password


@skipUnless(settings.PHARMACY_LEGACY_SCHEMA, "Requires legacy Staff/Role mappings.")
class LegacyStaffAuthTests(TestCase):
    @classmethod
    def setUpClass(cls):
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(Role)
            schema_editor.create_model(Staff)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(Staff)
            schema_editor.delete_model(Role)

    def setUp(self):
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO role (RoleName) VALUES (%s)", ["Cashier"])
            self.role_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO staff (RoleID, FullName, Email, IsActive) VALUES (%s, %s, %s, %s)",
                [self.role_id, "Legacy Cashier", "cashier@example.test", True],
            )
            self.staff_id = cursor.lastrowid
        self.staff = Staff.objects.get(pk=self.staff_id)
        StaffCredential.objects.create(
            staff=self.staff,
            email=self.staff.email,
            password_hash=make_password("legacy-login-password-123"),
        )

    def test_email_jwt_and_current_staff_use_legacy_ids_without_writing_staff(self):
        original_staff_row = (self.staff.role_id, self.staff.display_name, self.staff.email, self.staff.is_active)
        original_columns = {
            row.name for row in connection.introspection.get_table_description(connection.cursor(), "staff")
        }

        response = APIClient().post("/api/auth/token/", {
            "email": " CASHIER@example.test ", "password": "legacy-login-password-123",
        }, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(StaffCredential._meta.get_field("staff").column, "StaffID")
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(cursor, "staff_credentials")
        self.assertIn(
            ("staff", "StaffID"),
            [constraint["foreign_key"] for constraint in constraints.values() if constraint.get("foreign_key")],
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        current = client.get("/api/auth/me/")
        self.assertEqual(current.status_code, 200)
        self.assertEqual(current.data["id"], self.staff_id)
        self.assertEqual(current.data["username"], "cashier@example.test")
        self.assertEqual(current.data["display_name"], "Legacy Cashier")
        self.assertEqual(current.data["role"], "Cashier")
        self.assertEqual(current.data["permissions"], ["inventory.read", "sales.checkout", "sales.customer_lookup"])

        self.staff.refresh_from_db()
        self.assertEqual((self.staff.role_id, self.staff.display_name, self.staff.email, self.staff.is_active), original_staff_row)
        self.assertEqual(
            {row.name for row in connection.introspection.get_table_description(connection.cursor(), "staff")},
            original_columns,
        )

    def test_credential_password_change_only_updates_app_owned_table(self):
        legacy_row = (self.staff.role_id, self.staff.display_name, self.staff.email, self.staff.is_active)

        set_staff_password(self.staff, "replacement-legacy-password-987")

        credential = StaffCredential.objects.get(staff=self.staff)
        self.assertTrue(self.staff.check_password("replacement-legacy-password-987"))
        self.assertEqual(
            (self.staff.role_id, self.staff.display_name, self.staff.email, self.staff.is_active),
            legacy_row,
        )
        self.assertEqual(credential.email, "cashier@example.test")

    def test_inactive_legacy_staff_cannot_sign_in(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO staff (RoleID, FullName, Email, IsActive) VALUES (%s, %s, %s, %s)",
                [self.role_id, "Inactive Staff", "inactive@example.test", False],
            )
            inactive_id = cursor.lastrowid
        inactive = Staff.objects.get(pk=inactive_id)
        StaffCredential.objects.create(
            staff=inactive,
            email=inactive.email,
            password_hash=make_password("inactive-login-password-123"),
        )

        response = APIClient().post("/api/auth/token/", {
            "email": inactive.email, "password": "inactive-login-password-123",
        }, format="json")

        self.assertEqual(response.status_code, 401)