from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from api.models import ChurchCollaboration, Church, User
from api.serializers import (
    ChurchCollaborationSerializer,
    ChurchCollaborationCreateSerializer,
    ChurchCollaborationUpdateSerializer,
    ChurchCollaborationListSerializer,
    ChurchCollaborationApprovalSerializer
)


# =====================================================
# Create Collaboration
# =====================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_collaboration(request, church_id):
    """
    Create a new church collaboration
    Body: {
        "target_church_id": "UUID",
        "collaboration_type": "PARTNERSHIP|RESOURCE_SHARING|FATHER|OTHER",
        "start_date": "YYYY-MM-DD"
    }
    """
    try:
        church = Church.objects.get(id=church_id)
    except Church.DoesNotExist:
        return Response(
            {"error": "Church not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions - user must be church owner/admin
    from api.permissions import is_church_admin
    if not is_church_admin(request.user, church) and request.user.role != "SADMIN":
        return Response(
            {"error": "You don't have permission to create a collaboration"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = ChurchCollaborationCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    target_church_id = serializer.validated_data.pop('target_church_id')
    
    try:
        target_church = Church.objects.get(id=target_church_id)
    except Church.DoesNotExist:
        return Response(
            {"error": "Target church not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Prevent self-collaboration
    if church_id == target_church_id:
        return Response(
            {"error": "A church cannot collaborate with itself"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if collaboration already exists
    existing = ChurchCollaboration.objects.filter(
        Q(initiator_church=church, target_church=target_church) |
        Q(initiator_church=target_church, target_church=church)
    ).exists()
    
    if existing:
        return Response(
            {"error": "A collaboration already exists between these churches"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    collaboration = ChurchCollaboration.objects.create(
        initiator_church=church,
        target_church=target_church,
        created_by=request.user,
        **serializer.validated_data
    )
    
    return Response(
        ChurchCollaborationSerializer(collaboration).data,
        status=status.HTTP_201_CREATED
    )


# =====================================================
# Update Collaboration
# =====================================================

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_collaboration(request, church_id, collaboration_id):
    """
    Update a collaboration
    """
    try:
        church = Church.objects.get(id=church_id)
    except Church.DoesNotExist:
        return Response(
            {"error": "Church not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        collaboration = ChurchCollaboration.objects.get(id=collaboration_id)
    except ChurchCollaboration.DoesNotExist:
        return Response(
            {"error": "Collaboration not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    if collaboration.initiator_church.id != church_id and \
       collaboration.target_church.id != church_id:
        return Response(
            {"error": "This collaboration doesn't belong to this church"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Only initiator can update pending collaborations
    if collaboration.status == "PENDING" and \
       collaboration.initiator_church.id != church_id:
        return Response(
            {"error": "Only the initiator can modify a pending collaboration"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = ChurchCollaborationUpdateSerializer(
        collaboration, data=request.data, partial=True
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    
    return Response(ChurchCollaborationSerializer(collaboration).data)


# =====================================================
# Delete Collaboration
# =====================================================

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_collaboration(request, church_id, collaboration_id):
    """
    Delete a collaboration (only initiator can delete)
    """
    try:
        church = Church.objects.get(id=church_id)
    except Church.DoesNotExist:
        return Response(
            {"error": "Church not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        collaboration = ChurchCollaboration.objects.get(id=collaboration_id)
    except ChurchCollaboration.DoesNotExist:
        return Response(
            {"error": "Collaboration not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    if collaboration.initiator_church.id != church_id:
        return Response(
            {"error": "Only the initiator can delete a collaboration"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Can only delete pending or rejected collaborations
    if collaboration.status not in ["PENDING", "REJECTED"]:
        return Response(
            {"error": f"Cannot delete a {collaboration.get_status_display().lower()} collaboration"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    collaboration.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# =====================================================
# Retrieve Collaboration
# =====================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def retrieve_collaboration(request, church_id, collaboration_id):
    """
    Retrieve a single collaboration
    """
    try:
        church = Church.objects.get(id=church_id)
    except Church.DoesNotExist:
        return Response(
            {"error": "Church not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        collaboration = ChurchCollaboration.objects.get(id=collaboration_id)
    except ChurchCollaboration.DoesNotExist:
        return Response(
            {"error": "Collaboration not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check visibility
    if collaboration.initiator_church != church and collaboration.target_church != church:
        return Response(
            {"error": "You don't have access to this collaboration"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = ChurchCollaborationSerializer(collaboration)
    return Response(serializer.data)


# =====================================================
# List Church Collaborations
# =====================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_church_collaborations(request, church_id):
    """
    List all collaborations for a church
    Query params:
    - status: PENDING|ACCEPTED|REJECTED|ENDED
    - type: PARTNERSHIP|EVENT|RESOURCE_SHARING|MINISTRY|OTHER
    """
    try:
        church = Church.objects.get(id=church_id)
    except Church.DoesNotExist:
        return Response(
            {"error": "Church not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get all collaborations for this church (both initiator and target)
    collaborations = ChurchCollaboration.objects.filter(
        Q(initiator_church=church) | Q(target_church=church)
    )
    
    # Filter based on user role
    if request.user.role != "SADMIN":
        try:
            if request.user != church.owner:
                collaborations = collaborations.filter(status="ACCEPTED")
        except:
            pass
    
    # Filter by status if provided
    status_filter = request.query_params.get('status')
    if status_filter:
        collaborations = collaborations.filter(status=status_filter)
    
    # Filter by type if provided
    type_filter = request.query_params.get('type')
    if type_filter:
        collaborations = collaborations.filter(collaboration_type=type_filter)
    
    serializer = ChurchCollaborationListSerializer(collaborations, many=True)
    return Response({
        "count": collaborations.count(),
        "results": serializer.data
    })


# =====================================================
# List Pending Collaborations
# =====================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_pending_collaborations(request, church_id):
    """
    List pending collaboration requests for a church (church owner/admin only)
    """
    try:
        church = Church.objects.get(id=church_id)
    except Church.DoesNotExist:
        return Response(
            {"error": "Church not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions - must be church owner/admin
    from api.permissions import is_church_admin
    if not is_church_admin(request.user, church) and request.user.role != "SADMIN":
        return Response(
            {"error": "You don't have permission"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get pending collaborations where this church is the target
    collaborations = ChurchCollaboration.objects.filter(
        target_church=church,
        status="PENDING"
    )
    
    serializer = ChurchCollaborationListSerializer(collaborations, many=True)
    return Response({
        "count": collaborations.count(),
        "results": serializer.data
    })


# =====================================================
# Approve Collaboration
# =====================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_collaboration(request, church_id, collaboration_id):
    """
    Approve a collaboration request
    """
    try:
        church = Church.objects.get(id=church_id)
    except Church.DoesNotExist:
        return Response(
            {"error": "Church not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        collaboration = ChurchCollaboration.objects.get(id=collaboration_id)
    except ChurchCollaboration.DoesNotExist:
        return Response(
            {"error": "Collaboration not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    from api.permissions import is_church_admin
    if collaboration.target_church != church:
        return Response(
            {"error": "You don't have permission"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if not is_church_admin(request.user, church) and request.user.role != "SADMIN":
        return Response(
            {"error": "You don't have permission"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if collaboration.status != "PENDING":
        return Response(
            {"error": f"Cannot approve a {collaboration.get_status_display().lower()} collaboration"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    collaboration.accept(request.user)
    
    serializer = ChurchCollaborationSerializer(collaboration)
    return Response(
        {"message": "Collaboration approved successfully", "data": serializer.data},
        status=status.HTTP_200_OK
    )


# =====================================================
# Reject Collaboration
# =====================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_collaboration(request, church_id, collaboration_id):
    """
    Reject a collaboration request
    """
    try:
        church = Church.objects.get(id=church_id)
    except Church.DoesNotExist:
        return Response(
            {"error": "Church not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        collaboration = ChurchCollaboration.objects.get(id=collaboration_id)
    except ChurchCollaboration.DoesNotExist:
        return Response(
            {"error": "Collaboration not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions
    from api.permissions import is_church_admin
    if collaboration.target_church != church:
        return Response(
            {"error": "You don't have permission"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if not is_church_admin(request.user, church) and request.user.role != "SADMIN":
        return Response(
            {"error": "You don't have permission"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if collaboration.status != "PENDING":
        return Response(
            {"error": f"Cannot reject a {collaboration.get_status_display().lower()} collaboration"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    collaboration.reject()
    
    serializer = ChurchCollaborationSerializer(collaboration)
    return Response(
        {"message": "Collaboration rejected", "data": serializer.data},
        status=status.HTTP_200_OK
    )


# =====================================================
# End Collaboration
# =====================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def end_collaboration(request, church_id, collaboration_id):
    """
    Delete/End an active collaboration
    """
    try:
        church = Church.objects.get(id=church_id)
    except Church.DoesNotExist:
        return Response(
            {"error": "Church not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        collaboration = ChurchCollaboration.objects.get(id=collaboration_id)
    except ChurchCollaboration.DoesNotExist:
        return Response(
            {"error": "Collaboration not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check permissions - must be initiator or church owner
    from api.permissions import is_church_admin
    if collaboration.initiator_church != church and collaboration.target_church != church:
        return Response(
            {"error": "You don't have permission"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if collaboration.status != "ACCEPTED":
        return Response(
            {"error": "Only accepted collaborations can be ended"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    collaboration_data = ChurchCollaborationSerializer(collaboration).data
    collaboration.delete()
    
    return Response(
        {"message": "Collaboration ended", "data": collaboration_data},
        status=status.HTTP_200_OK
    )


# =====================================================
# Collaboration Statistics
# =====================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def collaboration_stats_for_church(request, church_id):
    """
    Get collaboration statistics for a church
    """
    try:
        church = Church.objects.get(id=church_id)
    except Church.DoesNotExist:
        return Response(
            {"error": "Church not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    collaborations = ChurchCollaboration.objects.filter(
        Q(initiator_church=church) | Q(target_church=church)
    )
    
    stats = {
        "total_collaborations": collaborations.count(),
        "pending": collaborations.filter(status="PENDING").count(),
        "accepted": collaborations.filter(status="ACCEPTED").count(),
        "rejected": collaborations.filter(status="REJECTED").count(),
        "ended": collaborations.filter(status="ENDED").count(),
        "by_type": {
            "partnerships": collaborations.filter(collaboration_type="PARTNERSHIP").count(),
            "events": collaborations.filter(collaboration_type="EVENT").count(),
            "resource_sharing": collaborations.filter(collaboration_type="RESOURCE_SHARING").count(),
            "ministries": collaborations.filter(collaboration_type="MINISTRY").count(),
        }
    }
    
    return Response(stats)

