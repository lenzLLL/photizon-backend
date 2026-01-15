from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum
from django.utils import timezone
import uuid

from api.models import Receipt, Church, ChurchAdmin
from api.serializers import ReceiptSerializer
from api.permissions import IsChurchAdmin, IsAuthenticatedUser


class ReceiptViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Receipt CRUD operations.
    Only accessible to church admins (OWNER or ADMIN role).
    
    Endpoints:
    - GET /receipts/ - List all receipts for user's churches
    - POST /receipts/ - Create a new receipt
    - GET /receipts/{id}/ - Get receipt details
    - PUT /receipts/{id}/ - Update receipt
    - DELETE /receipts/{id}/ - Delete receipt
    - GET /receipts/church/{church_id}/ - Get receipts for specific church
    - GET /receipts/church/{church_id}/stats/ - Get stats for specific church
    """
    serializer_class = ReceiptSerializer
    permission_classes = [IsChurchAdmin]
    
    def get_queryset(self):
        """Filter receipts for churches where user is admin"""
        user = self.request.user
        
        # SuperAdmin can see all receipts
        if getattr(user, "role", None) == "SADMIN":
            return Receipt.objects.all().order_by("-issued_at")
        
        # Get churches where user is admin
        admin_churches = ChurchAdmin.objects.filter(
            user=user,
            role__in=["OWNER", "ADMIN"]
        ).values_list("church_id", flat=True)
        
        # Return receipts only for these churches
        return Receipt.objects.filter(church_id__in=admin_churches).order_by("-issued_at")
    
    def perform_create(self, serializer):
        """Auto-generate receipt and validate church access"""
        user = self.request.user
        church_id = self.request.data.get("church")
        
        if not church_id:
            raise ValueError("Church is required")
        
        church = get_object_or_404(Church, id=church_id)
        
        # Verify user is admin of this church
        is_admin = ChurchAdmin.objects.filter(
            user=user,
            church=church,
            role__in=["OWNER", "ADMIN"]
        ).exists()
        
        if not is_admin and getattr(user, "role", None) != "SADMIN":
            raise PermissionError("You are not an admin of this church")
        
        serializer.save(church=church)
    
    def perform_update(self, serializer):
        """Ensure only admins of the church can update"""
        user = self.request.user
        receipt = self.get_object()
        
        # Verify user is admin of the receipt's church
        is_admin = ChurchAdmin.objects.filter(
            user=user,
            church=receipt.church,
            role__in=["OWNER", "ADMIN"]
        ).exists()
        
        if not is_admin and getattr(user, "role", None) != "SADMIN":
            raise PermissionError("You are not an admin of this church")
        
        serializer.save()
    
    def perform_destroy(self, instance):
        """Ensure only admins of the church can delete"""
        user = self.request.user
        
        # Verify user is admin of the receipt's church
        is_admin = ChurchAdmin.objects.filter(
            user=user,
            church=instance.church,
            role__in=["OWNER", "ADMIN"]
        ).exists()
        
        if not is_admin and getattr(user, "role", None) != "SADMIN":
            raise PermissionError("You are not an admin of this church")
        
        instance.delete()
    
    @action(detail=False, methods=["GET"])
    def all(self, request):
        """Get all receipts for user's churches"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=["GET"])
    def detail(self, request, pk=None):
        """Get receipt details by ID"""
        receipt = self.get_object()
        serializer = self.get_serializer(receipt)
        return Response(serializer.data)
    
    @action(detail=False, methods=["GET"], url_path="church/(?P<church_id>[^/]+)")
    def receipts_by_church(self, request, church_id=None):
        """Get all receipts for a specific church"""
        church = get_object_or_404(Church, id=church_id)
        
        # Verify user is admin of this church
        is_admin = ChurchAdmin.objects.filter(
            user=request.user,
            church=church,
            role__in=["OWNER", "ADMIN"]
        ).exists()
        
        if not is_admin and getattr(request.user, "role", None) != "SADMIN":
            return Response(
                {"detail": "You are not an admin of this church"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        receipts = Receipt.objects.filter(church=church).order_by("-issued_at")
        serializer = self.get_serializer(receipts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=["GET"], url_path="church/(?P<church_id>[^/]+)/stats")
    def church_receipt_stats(self, request, church_id=None):
        """Get receipt statistics for a church"""
        church = get_object_or_404(Church, id=church_id)
        
        # Verify user is admin of this church
        is_admin = ChurchAdmin.objects.filter(
            user=request.user,
            church=church,
            role__in=["OWNER", "ADMIN"]
        ).exists()
        
        if not is_admin and getattr(request.user, "role", None) != "SADMIN":
            return Response(
                {"detail": "You are not an admin of this church"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        receipts = Receipt.objects.filter(church=church)
        
        stats = {
            "total_receipts": receipts.count(),
            "total_amount": receipts.aggregate(Sum("amount"))["amount__sum"] or 0,
        }
        
        return Response(stats)


@api_view(["POST"])
@permission_classes([IsChurchAdmin])
def create_receipt(request, church_id):
    """Create a new receipt for a church"""
    church = get_object_or_404(Church, id=church_id)
    
    # Verify user is admin of this church
    is_admin = ChurchAdmin.objects.filter(
        user=request.user,
        church=church,
    ).exists()
    
    if not is_admin and getattr(request.user, "role", None) != "SADMIN":
        return Response(
            {"detail": "You are not an admin of this church"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    data = request.data.copy()
    data["church"] = church.id
    
    serializer = ReceiptSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsChurchAdmin])
def get_receipt(request, receipt_id):
    """Get a specific receipt by ID"""
    receipt = get_object_or_404(Receipt, id=receipt_id)
    
    # Verify user is admin of the receipt's church
    is_admin = ChurchAdmin.objects.filter(
        user=request.user,
        church=receipt.church,
        role__in=["OWNER", "ADMIN"]
    ).exists()
    
    if not is_admin and getattr(request.user, "role", None) != "SADMIN":
        return Response(
            {"detail": "You are not an admin of this church"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = ReceiptSerializer(receipt)
    return Response(serializer.data)


@api_view(["PUT", "PATCH"])
@permission_classes([IsChurchAdmin])
def update_receipt(request, receipt_id):
    """Update a receipt"""
    receipt = get_object_or_404(Receipt, id=receipt_id)
    
    # Verify user is admin of the receipt's church
    is_admin = ChurchAdmin.objects.filter(
        user=request.user,
        church=receipt.church,
        role__in=["OWNER", "ADMIN"]
    ).exists()
    
    if not is_admin and getattr(request.user, "role", None) != "SADMIN":
        return Response(
            {"detail": "You are not an admin of this church"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = ReceiptSerializer(receipt, data=request.data, partial=(request.method == "PATCH"))
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE"])
@permission_classes([IsChurchAdmin])
def delete_receipt(request, receipt_id):
    """Delete a receipt"""
    receipt = get_object_or_404(Receipt, id=receipt_id)
    
    # Verify user is admin of the receipt's church
    is_admin = ChurchAdmin.objects.filter(
        user=request.user,
        church=receipt.church,
        role__in=["OWNER", "ADMIN"]
    ).exists()
    
    if not is_admin and getattr(request.user, "role", None) != "SADMIN":
        return Response(
            {"detail": "You are not an admin of this church"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    receipt.delete()
    return Response({"detail": "Receipt deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsChurchAdmin])
def list_all_receipts(request):
    """Get all receipts for user's churches with filters"""
    from django.db.models import Q
    
    user = request.user
    
    # SuperAdmin can see all receipts
    if getattr(user, "role", None) == "SADMIN":
        receipts = Receipt.objects.all().order_by("-issued_at")
    else:
        # Get churches where user is admin
        admin_churches = ChurchAdmin.objects.filter(
            user=user,
            role__in=["OWNER", "ADMIN"]
        ).values_list("church_id", flat=True)
        
        receipts = Receipt.objects.filter(church_id__in=admin_churches).order_by("-issued_at")
    
    # Filters
    church_id = request.GET.get("church")
    content_id = request.GET.get("content")
    amount_min = request.GET.get("amount_min")
    amount_max = request.GET.get("amount_max")
    issued_after = request.GET.get("issued_after")
    issued_before = request.GET.get("issued_before")
    
    # Filter by church
    if church_id:
        receipts = receipts.filter(church_id=church_id)
    
    # Filter by content
    if content_id:
        receipts = receipts.filter(content_id=content_id)
    
    # Filter by amount range
    if amount_min:
        try:
            receipts = receipts.filter(amount__gte=float(amount_min))
        except ValueError:
            pass
    
    if amount_max:
        try:
            receipts = receipts.filter(amount__lte=float(amount_max))
        except ValueError:
            pass
    
    # Filter by issued_at date range
    if issued_after:
        try:
            from django.utils.dateparse import parse_datetime
            issued_after_dt = parse_datetime(issued_after)
            if issued_after_dt:
                receipts = receipts.filter(issued_at__gte=issued_after_dt)
        except:
            pass
    
    if issued_before:
        try:
            from django.utils.dateparse import parse_datetime
            issued_before_dt = parse_datetime(issued_before)
            if issued_before_dt:
                receipts = receipts.filter(issued_at__lte=issued_before_dt)
        except:
            pass
    
    serializer = ReceiptSerializer(receipts, many=True)
    return Response(serializer.data)
