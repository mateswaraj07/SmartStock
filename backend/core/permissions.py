from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    def has_permission(self, request, view):
        return getattr(request.user, "role", None) == "OWNER"


class IsSupplier(BasePermission):
    def has_permission(self, request, view):
        return getattr(request.user, "role", None) == "SUPPLIER"
