from django.contrib.auth.hashers import check_password, make_password
from django.db import models


class Role(models.Model):
    id = models.AutoField(db_column="RoleID", primary_key=True)
    name = models.CharField(db_column="RoleName", max_length=50, unique=True)

    class Meta:
        managed = False
        db_table = "role"

    @property
    def description(self):
        return ""

    @property
    def permissions(self):
        from .management.commands.bootstrap_roles import DEFAULT_ROLES

        return DEFAULT_ROLES.get(self.name, [])

    @property
    def is_active(self):
        return bool(self.permissions)

    def save(self, *args, **kwargs):
        raise RuntimeError("Legacy role rows are read-only in legacy schema mode.")

    def delete(self, *args, **kwargs):
        raise RuntimeError("Legacy role rows are read-only in legacy schema mode.")


class LegacyStaffManager(models.Manager):
    def get_by_natural_key(self, email):
        return self.get(email__iexact=email)


class Staff(models.Model):
    id = models.AutoField(db_column="StaffID", primary_key=True)
    role = models.ForeignKey(
        Role, db_column="RoleID", on_delete=models.DO_NOTHING,
        related_name="staff_members", null=True, blank=True,
    )
    display_name = models.CharField(db_column="FullName", max_length=150)
    email = models.EmailField(db_column="Email", max_length=254, unique=True)
    is_active = models.BooleanField(db_column="IsActive", default=True)
    objects = LegacyStaffManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        managed = False
        db_table = "staff"

    @property
    def username(self):
        return self.email

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    @property
    def is_staff(self):
        return bool(self.role and "staff.manage" in self.role.permissions)

    @property
    def is_superuser(self):
        return False

    def get_username(self):
        return self.email

    def has_perm(self, permission, obj=None):
        return bool(self.role and permission in self.role.permissions)

    def has_module_perms(self, app_label):
        return self.is_staff

    def set_password(self, raw_password):
        from .models import StaffCredential

        StaffCredential.objects.update_or_create(
            staff_id=self.pk,
            defaults={
                "email": self.email.strip().casefold(),
                "password_hash": make_password(raw_password),
            },
        )

    def check_password(self, raw_password):
        from .models import StaffCredential

        credential = StaffCredential.objects.filter(staff_id=self.pk).first()
        return bool(credential and check_password(raw_password, credential.password_hash))

    def save(self, *args, **kwargs):
        raise RuntimeError("Legacy staff rows are read-only; only credentials may be changed.")

    def delete(self, *args, **kwargs):
        raise RuntimeError("Legacy staff rows are read-only; only credentials may be changed.")

    def __str__(self):
        return self.display_name