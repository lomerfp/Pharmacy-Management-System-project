import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Role",
            fields=[
                ("id", models.AutoField(db_column="RoleID", primary_key=True, serialize=False)),
                ("name", models.CharField(db_column="RoleName", max_length=50, unique=True)),
            ],
            options={"db_table": "role", "managed": False},
        ),
        migrations.CreateModel(
            name="Staff",
            fields=[
                ("id", models.AutoField(db_column="StaffID", primary_key=True, serialize=False)),
                ("display_name", models.CharField(db_column="FullName", max_length=150)),
                ("email", models.EmailField(db_column="Email", max_length=254, unique=True)),
                ("is_active", models.BooleanField(db_column="IsActive", default=True)),
                ("role", models.ForeignKey(blank=True, db_column="RoleID", null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name="staff_members", to="pharmacy.role")),
            ],
            options={"db_table": "staff", "managed": False},
        ),
        migrations.CreateModel(
            name="StaffCredential",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("password_hash", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("staff", models.OneToOneField(db_column="StaffID", on_delete=django.db.models.deletion.CASCADE, related_name="credential", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "staff_credentials"},
        ),
        migrations.CreateModel(
            name="PasswordResetToken",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token_digest", models.CharField(max_length=64, unique=True)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("consumed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("staff", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="password_reset_tokens", to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]