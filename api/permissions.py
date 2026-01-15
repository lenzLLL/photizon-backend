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

class IsChurchAdmin(BasePermission):
    """Permission to check if user is a church admin (OWNER or ADMIN role)"""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # SuperAdmin has all access
        if getattr(request.user, "role", None) == "SADMIN":
            return True
        # Check if user has at least one church admin role
        return ChurchAdmin.objects.filter(
            user=request.user,
        ).exists()
    
    def has_object_permission(self, request, view, obj):
        # SuperAdmin has all access
        if getattr(request.user, "role", None) == "SADMIN":
            return True
        # Check if user is admin of the church related to this receipt
        if hasattr(obj, 'church') and obj.church:
            return ChurchAdmin.objects.filter(
                user=request.user,
                church=obj.church,
                role__in=["OWNER", "ADMIN"]
            ).exists()
        return False

def is_church_admin(user, church):
    return ChurchAdmin.objects.filter(
        user=user,
        church=church,
        role__in=["OWNER", "ADMIN"]
    ).exists()

def user_is_church_admin(user, church):
    return user.role == "SADMIN" or \
           ChurchAdmin.objects.filter(church=church, user=user).exists()

def user_is_church_owner(user, church):
    # SuperAdmin a toujours accès
    if user.role == "SADMIN":
        return True

    # Vérifier si l'utilisateur est OWNER dans ChurchAdmin
    return ChurchAdmin.objects.filter(
        user=user,
        church=church,
        role__in=["OWNER"]
    ).exists()
