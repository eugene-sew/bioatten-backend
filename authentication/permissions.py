from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner of the object
        return obj == request.user or request.user.is_admin()


class IsAdmin(permissions.BasePermission):
    """
    Custom permission to only allow admin users.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_admin()


class IsStudent(permissions.BasePermission):
    """
    Custom permission to only allow student users.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_student()


class IsFaculty(permissions.BasePermission):
    """
    Custom permission to only allow faculty users.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_faculty()


class IsAdminOrFaculty(permissions.BasePermission):
    """
    Custom permission to allow admin or faculty users.
    """
    
    def has_permission(self, request, view):
        return (request.user and request.user.is_authenticated and 
                (request.user.is_admin() or request.user.is_faculty()))


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to allow owners or admin users.
    """
    
    def has_object_permission(self, request, view, obj):
        # Check if the object has a user attribute
        if hasattr(obj, 'user'):
            return obj.user == request.user or request.user.is_admin()
        # If the object is a user instance itself
        return obj == request.user or request.user.is_admin()


class IsAuthenticatedAndActive(permissions.BasePermission):
    """
    Custom permission to check if user is authenticated and active.
    """
    
    def has_permission(self, request, view):
        return (request.user and 
                request.user.is_authenticated and 
                request.user.is_active)
