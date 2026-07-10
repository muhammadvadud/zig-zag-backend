from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsOwner(BasePermission):
    """Object-level guard: the object must belong to request.user (IDOR shield).

    Views must also filter their queryset by the user; this is the second
    layer covering object lookups.
    """

    owner_field = "user"

    def has_object_permission(self, request, view, obj):
        owner_field = getattr(view, "owner_field", self.owner_field)
        owner = getattr(obj, owner_field, None)
        return owner == request.user


class IsStaffRole(BasePermission):
    """Manager or admin role."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role in ("manager", "admin"))


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == "admin")


class IsOrderStaff(BasePermission):
    """Employee, manager or admin — anyone whose job touches order fulfilment."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and user.role in ("employee", "manager", "admin")
        )


class ReadOnlyOrStaff(BasePermission):
    """Anyone can read; only staff can write."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return bool(user and user.is_authenticated and user.role in ("manager", "admin"))
