from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from collections import Counter


def migrate_staff_passwords(apps, schema_editor):
    Staff = apps.get_model("pharmacy", "Staff")
    StaffCredential = apps.get_model("pharmacy", "StaffCredential")
    database = schema_editor.connection.alias
    staff_rows = list(Staff.objects.using(database).all().iterator())
    email_counts = Counter((staff.email or "").strip().casefold() for staff in staff_rows)

    for staff in staff_rows:
        email = (staff.email or "").strip().casefold()
        if not email or email_counts[email] != 1 or not staff.password or staff.password.startswith("!"):
            continue
        StaffCredential.objects.using(database).create(
            staff_id=staff.pk,
            email=email,
            password_hash=staff.password,
        )
        Staff.objects.using(database).filter(pk=staff.pk).update(password="!")


class Migration(migrations.Migration):
    dependencies = [("pharmacy", "0002_pharmacysetting_alter_staff_display_name_and_more")]

    operations = [
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
        migrations.RunPython(migrate_staff_passwords, migrations.RunPython.noop),
    ]