from rest_framework.permissions import BasePermission


class HasRolePermission(BasePermission):
    """Require an explicit permission key in the staff member's assigned role."""
    message = "Your role does not allow this action."

    def has_permission(self, request, view):
        user = request.user
        required = getattr(view, "required_permission", None)
        if not user or not user.is_authenticated or not user.is_active:
            return False
        if required is None:
            return True
        role = getattr(user, "role", None)
        if not role or not role.is_active:
            return False
        return required in role.permissions
