from django.contrib.auth.hashers import check_password

from .models import Staff, StaffCredential


class StaffCredentialBackend:
    def authenticate(self, request, username=None, email=None, password=None, **kwargs):
        login_email = (email or username or "").strip().casefold()
        if not login_email or password is None:
            return None
        credential = StaffCredential.objects.select_related("staff").filter(email__iexact=login_email).first()
        if (
            credential
            and credential.staff.is_active
            and credential.staff.email.strip().casefold() == login_email
            and check_password(password, credential.password_hash)
        ):
            return credential.staff
        return None

    def get_user(self, user_id):
        try:
            return Staff.objects.get(pk=user_id)
        except Staff.DoesNotExist:
            return None