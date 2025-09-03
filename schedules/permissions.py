from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdminOrFacultyForWrite(BasePermission):
    """
    Allow read-only methods for authenticated users (handled by global IsAuthenticated),
    but restrict unsafe methods (POST/PUT/PATCH/DELETE) to Admins or Faculty.
    """

    def has_permission(self, request, view):
        # Always allow safe methods; authentication is enforced by global settings or viewset.
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Allow if user has admin or faculty role, or is staff.
        role = getattr(user, 'role', None)
        return getattr(user, 'is_staff', False) or role in ('ADMIN', 'FACULTY')
