from rest_framework.permissions import BasePermission

from api.models import ChurchAdmin

class IsAuthenticatedUser(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, "role", None) == "SADMIN"

class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, "role", None) == "ADMIN"

def is_church_admin(user, church):
    return ChurchAdmin.objects.filter(
        user=user,
        church=church,
        role__in=["OWNER", "ADMIN"]
    ).exists()

def user_is_church_admin(user, church):
    return user.role == "SADMIN" or \
           ChurchAdmin.objects.filter(church=church, user=user).exists()