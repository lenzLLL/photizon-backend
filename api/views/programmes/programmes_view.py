from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from api.models import Programme, Church, User, Content, ProgrammeMember
from api.serializers import (
    ProgrammeSerializer,
    ProgrammeCreateSerializer,
    ProgrammeUpdateSerializer,
    ProgrammeListSerializer,
    ProgrammeContentSerializer,
    ProgrammeMemberSerializer,
    ProgrammeWithMembersSerializer
)
from api.permissions import IsAuthenticatedUser


# =====================================================
# Create Programme
# =====================================================

@api_view(['POST'])
@permission_classes([IsAuthenticatedUser])
def create_programme(request, church_id):
    """
    Créer un nouveau programme pour une église
    Body: {
        "title": "string",
        "description": "string",
        "cover_image_url": "URL",
        "start_date": "YYYY-MM-DD",
        "end_date": "YYYY-MM-DD",
        "is_public": boolean
    }
    """
    try:
        church = Church.objects.get(id=church_id)
    except Church.DoesNotExist:
        return Response(
            {"error": "Église non trouvée"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Vérifier les permissions - admin d'église ou SADMIN
    from api.permissions import is_church_admin
    if not is_church_admin(request.user, church) and request.user.role != "SADMIN":
        return Response(
            {"error": "Vous devez être administrateur de cette église"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = ProgrammeCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    programme = Programme.objects.create(
        church=church,
        created_by=request.user,
        **serializer.validated_data
    )
    
    return Response(
        ProgrammeSerializer(programme).data,
        status=status.HTTP_201_CREATED
    )


# =====================================================
# Retrieve Programme
# =====================================================

@api_view(['GET'])
@permission_classes([IsAuthenticatedUser])
def retrieve_programme(request, church_id, programme_id):
    """
    Récupérer les détails d'un programme
    """
    try:
        church = Church.objects.get(id=church_id)
    except Church.DoesNotExist:
        return Response(
            {"error": "Église non trouvée"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        programme = Programme.objects.get(id=programme_id, church=church)
    except Programme.DoesNotExist:
        return Response(
            {"error": "Programme non trouvé"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Vérification de visibilité
    if programme.status == "DRAFT" and request.user.current_church_id != church.id:
        return Response(
            {"error": "Vous n'avez pas accès à ce programme"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = ProgrammeSerializer(programme)
    return Response(serializer.data)


# =====================================================
# Update Programme
# =====================================================

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticatedUser])
def update_programme(request, church_id, programme_id):
    """
    Mettre à jour un programme
    """
    try:
        church = Church.objects.get(id=church_id)
    except Church.DoesNotExist:
        return Response(
            {"error": "Église non trouvée"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        programme = Programme.objects.get(id=programme_id, church=church)
    except Programme.DoesNotExist:
        return Response(
            {"error": "Programme non trouvé"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Vérifier les permissions
    from api.permissions import is_church_admin
    if not is_church_admin(request.user, church) and request.user.role != "SADMIN":
        return Response(
            {"error": "Vous devez être administrateur de cette église"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = ProgrammeUpdateSerializer(
        programme, data=request.data, partial=True
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    
    return Response(ProgrammeSerializer(programme).data)


# =====================================================
# Delete Programme
# =====================================================

@api_view(['DELETE'])
@permission_classes([IsAuthenticatedUser])
def delete_programme(request, church_id, programme_id):
    """
    Supprimer un programme (admin d'église ou SADMIN)
    """
    try:
        church = Church.objects.get(id=church_id)
    except Church.DoesNotExist:
        return Response(
            {"error": "Église non trouvée"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        programme = Programme.objects.get(id=programme_id, church=church)
    except Programme.DoesNotExist:
        return Response(
            {"error": "Programme non trouvé"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Vérifier les permissions
    from api.permissions import is_church_admin
    if not is_church_admin(request.user, church) and request.user.role != "SADMIN":
        return Response(
            {"error": "Vous devez être administrateur de cette église"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    programme.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# =====================================================
# List Church Programmes
# =====================================================

@api_view(['GET'])
@permission_classes([IsAuthenticatedUser])
def list_church_programmes(request, church_id):
    """
    Lister tous les programmes d'une église
    Query params: status, is_public, limit, offset
    """
    try:
        church = Church.objects.get(id=church_id)
    except Church.DoesNotExist:
        return Response(
            {"error": "Église non trouvée"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Vérifier que l'utilisateur est membre
    if request.user.current_church_id != church.id and request.user.role != "SADMIN":
        return Response(
            {"error": "Vous devez être membre de cette église"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    programmes = Programme.objects.filter(church=church).select_related(
        'church', 'created_by'
    ).prefetch_related(
        'content_items'
    ).order_by('-start_date')
    
    # Filtrer par statut
    status_filter = request.query_params.get('status')
    if status_filter:
        programmes = programmes.filter(status=status_filter)
    
    # Filtrer par visibilité
    is_public = request.query_params.get('is_public')
    if is_public:
        programmes = programmes.filter(is_public=is_public.lower() == 'true')
    
    # Pagination infinie
    try:
        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))
    except ValueError:
        limit = 20
        offset = 0
    
    limit = min(limit, 100)
    total_count = programmes.count()
    paginated_programmes = programmes[offset:offset + limit]
    
    serializer = ProgrammeListSerializer(paginated_programmes, many=True)
    
    return Response({
        "count": total_count,
        "limit": limit,
        "offset": offset,
        "next_offset": offset + limit if offset + limit < total_count else None,
        "results": serializer.data
    })


# =====================================================
# Add Content to Programme
# =====================================================

@api_view(['POST'])
@permission_classes([IsAuthenticatedUser])
def add_content_to_programme(request, church_id, programme_id):
    """
    Ajouter du contenu (événements, enseignements) au programme
    Crée automatiquement des notifications pour tous les membres
    Body: {
        "content_id": "UUID"
    }
    """
    try:
        church = Church.objects.get(id=church_id)
    except Church.DoesNotExist:
        return Response(
            {"error": "Église non trouvée"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        programme = Programme.objects.get(id=programme_id, church=church)
    except Programme.DoesNotExist:
        return Response(
            {"error": "Programme non trouvé"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Vérifier les permissions
    from api.permissions import is_church_admin
    if not is_church_admin(request.user, church) and request.user.role != "SADMIN":
        return Response(
            {"error": "Vous devez être administrateur de cette église"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    content_id = request.data.get('content_id')
    if not content_id:
        return Response(
            {"error": "content_id requis"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        content = Content.objects.get(id=content_id, church=church)
    except Content.DoesNotExist:
        return Response(
            {"error": "Contenu non trouvé ou ne appartient pas à cette église"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Vérifier que le contenu n'est pas déjà dans le programme
    if programme.content_items.filter(id=content_id).exists():
        return Response(
            {"error": "Ce contenu est déjà dans le programme"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    programme.content_items.add(content)
    
    # 🔔 Créer des notifications pour tous les membres du programme
    # Même si le contenu est "coming soon", les membres sont notifiés
    from django.utils import timezone
    from api.models import ProgrammeContentNotification
    
    members = programme.members.all()
    notifications_created = 0
    
    for member in members:
        # Vérifier que la notification n'existe pas déjà pour ce jour
        existing = ProgrammeContentNotification.objects.filter(
            programme=programme,
            content=content,
            user=member.user,
            created_at__date=timezone.now().date()
        ).exists()
        
        if not existing:
            ProgrammeContentNotification.objects.create(
                programme=programme,
                content=content,
                user=member.user,
                is_notified=True  # Notification sent immediately
            )
            notifications_created += 1
    
    return Response({
        "message": "Contenu ajouté au programme",
        "notifications_sent": notifications_created,
        "programme": ProgrammeContentSerializer(programme).data
    }, status=status.HTTP_200_OK)


# =====================================================
# Remove Content from Programme
# =====================================================

@api_view(['POST'])
@permission_classes([IsAuthenticatedUser])
def remove_content_from_programme(request, church_id, programme_id):
    """
    Retirer du contenu du programme
    Body: {
        "content_id": "UUID"
    }
    """
    try:
        church = Church.objects.get(id=church_id)
    except Church.DoesNotExist:
        return Response(
            {"error": "Église non trouvée"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        programme = Programme.objects.get(id=programme_id, church=church)
    except Programme.DoesNotExist:
        return Response(
            {"error": "Programme non trouvé"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Vérifier les permissions
    from api.permissions import is_church_admin
    if not is_church_admin(request.user, church) and request.user.role != "SADMIN":
        return Response(
            {"error": "Vous devez être administrateur de cette église"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    content_id = request.data.get('content_id')
    if not content_id:
        return Response(
            {"error": "content_id requis"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not programme.content_items.filter(id=content_id).exists():
        return Response(
            {"error": "Ce contenu n'est pas dans le programme"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    programme.content_items.remove(content_id)
    
    return Response(
        ProgrammeContentSerializer(programme).data,
        status=status.HTTP_200_OK
    )


# =====================================================
# Get Programme Content
# =====================================================

@api_view(['GET'])
@permission_classes([IsAuthenticatedUser])
def get_programme_content(request, church_id, programme_id):
    """
    Récupérer tous les contenus d'un programme
    """
    try:
        church = Church.objects.get(id=church_id)
    except Church.DoesNotExist:
        return Response(
            {"error": "Église non trouvée"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        programme = Programme.objects.get(id=programme_id, church=church)
    except Programme.DoesNotExist:
        return Response(
            {"error": "Programme non trouvé"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = ProgrammeContentSerializer(programme)
    return Response(serializer.data)


# =====================================================
# Programme Statistics
# =====================================================

@api_view(['GET'])
@permission_classes([IsAuthenticatedUser])
def programme_stats_for_church(request, church_id):
    """
    Statistiques des programmes d'une église
    """
    try:
        church = Church.objects.get(id=church_id)
    except Church.DoesNotExist:
        return Response(
            {"error": "Église non trouvée"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    programmes = Programme.objects.filter(church=church)
    
    from django.db.models import Count
    from django.utils import timezone
    
    today = timezone.now().date()
    
    stats = {
        "total_programmes": programmes.count(),
        "active_programmes": programmes.filter(
            start_date__lte=today,
            end_date__gte=today
        ).count(),
        "upcoming_programmes": programmes.filter(
            start_date__gt=today
        ).count(),
        "archived_programmes": programmes.filter(
            status="ARCHIVED"
        ).count(),
        "by_status": dict(
            programmes.values('status').annotate(count=Count('id')).values_list('status', 'count')
        ),
        "by_visibility": {
            "public": programmes.filter(is_public=True).count(),
            "private": programmes.filter(is_public=False).count(),
        },
        "total_content_items": sum(p.get_event_count() for p in programmes),
    }
    
    return Response(stats)


# =====================================================
# Join Programme
# =====================================================

@api_view(['POST'])
@permission_classes([IsAuthenticatedUser])
def join_programme(request, church_id, programme_id):
    """
    Rejoindre un programme
    """
    try:
        church = Church.objects.get(id=church_id)
    except Church.DoesNotExist:
        return Response(
            {"error": "Église non trouvée"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        programme = Programme.objects.get(id=programme_id, church=church)
    except Programme.DoesNotExist:
        return Response(
            {"error": "Programme non trouvé"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Vérifier la visibilité du programme
    # Si privé, l'utilisateur doit être membre de l'église
    if not programme.is_public and request.user.current_church_id != church.id:
        return Response(
            {"error": "Vous n'avez pas accès à ce programme"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Vérifier que l'utilisateur n'est pas déjà membre
    if programme.members.filter(user=request.user).exists():
        return Response(
            {"error": "Vous êtes déjà membre de ce programme"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Ajouter l'utilisateur au programme
    member = ProgrammeMember.objects.create(
        programme=programme,
        user=request.user
    )
    
    serializer = ProgrammeMemberSerializer(member)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# =====================================================
# Leave Programme
# =====================================================

@api_view(['POST'])
@permission_classes([IsAuthenticatedUser])
def leave_programme(request, church_id, programme_id):
    """
    Quitter un programme
    """
    try:
        church = Church.objects.get(id=church_id)
    except Church.DoesNotExist:
        return Response(
            {"error": "Église non trouvée"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        programme = Programme.objects.get(id=programme_id, church=church)
    except Programme.DoesNotExist:
        return Response(
            {"error": "Programme non trouvé"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Vérifier que l'utilisateur est membre
    try:
        member = ProgrammeMember.objects.get(programme=programme, user=request.user)
    except ProgrammeMember.DoesNotExist:
        return Response(
            {"error": "Vous n'êtes pas membre de ce programme"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    member.delete()
    
    return Response(
        {"message": "Vous avez quitté le programme"},
        status=status.HTTP_200_OK
    )


# =====================================================
# Get Programme Members
# =====================================================

@api_view(['GET'])
@permission_classes([IsAuthenticatedUser])
def get_programme_members(request, church_id, programme_id):
    """
    Récupérer la liste des membres d'un programme
    Query params: limit, offset
    """
    try:
        church = Church.objects.get(id=church_id)
    except Church.DoesNotExist:
        return Response(
            {"error": "Église non trouvée"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        programme = Programme.objects.get(id=programme_id, church=church)
    except Programme.DoesNotExist:
        return Response(
            {"error": "Programme non trouvé"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Vérifier que l'utilisateur a accès au programme
    if not programme.is_public and request.user.current_church_id != church.id:
        return Response(
            {"error": "Vous n'avez pas accès à ce programme"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    members = ProgrammeMember.objects.filter(
        programme=programme
    ).select_related('user').order_by('-joined_at')
    
    # Pagination
    try:
        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))
    except ValueError:
        limit = 20
        offset = 0
    
    limit = min(limit, 100)
    total_count = members.count()
    paginated_members = members[offset:offset + limit]
    
    serializer = ProgrammeMemberSerializer(paginated_members, many=True)
    
    return Response({
        "count": total_count,
        "limit": limit,
        "offset": offset,
        "next_offset": offset + limit if offset + limit < total_count else None,
        "results": serializer.data
    })


# =====================================================
# Programme Content Notifications
# =====================================================

@api_view(['GET'])
@permission_classes([IsAuthenticatedUser])
def get_programme_content_notifications(request, church_id, programme_id):
    """
    Récupérer les notifications de contenu du programme
    L'utilisateur ne voit que SES notifications
    Query params: limit, offset, is_read
    """
    try:
        church = Church.objects.get(id=church_id)
    except Church.DoesNotExist:
        return Response(
            {"error": "Église non trouvée"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        programme = Programme.objects.get(id=programme_id, church=church)
    except Programme.DoesNotExist:
        return Response(
            {"error": "Programme non trouvé"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Vérifier que l'utilisateur est membre du programme
    is_member = programme.members.filter(user=request.user).exists()
    if not is_member and request.user.role != "SADMIN":
        return Response(
            {"error": "Vous devez être membre du programme"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Récupérer les notifications de l'utilisateur
    from api.models import ProgrammeContentNotification
    notifications = ProgrammeContentNotification.objects.filter(
        programme=programme,
        user=request.user
    ).select_related('content').order_by('-created_at')
    
    # Filtrer par is_read si fourni
    is_read = request.query_params.get('is_read')
    if is_read is not None:
        is_read_bool = is_read.lower() in ['true', '1', 'yes']
        notifications = notifications.filter(is_read=is_read_bool)
    
    # Pagination
    try:
        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))
    except ValueError:
        limit = 20
        offset = 0
    
    limit = min(limit, 100)
    total_count = notifications.count()
    paginated = notifications[offset:offset + limit]
    
    from api.serializers import ProgrammeContentNotificationListSerializer
    serializer = ProgrammeContentNotificationListSerializer(paginated, many=True)
    
    return Response({
        "count": total_count,
        "limit": limit,
        "offset": offset,
        "next_offset": offset + limit if offset + limit < total_count else None,
        "results": serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticatedUser])
def mark_programme_notification_as_read(request, church_id, programme_id, notification_id):
    """
    Marquer une notification de programme comme lue
    """
    try:
        church = Church.objects.get(id=church_id)
    except Church.DoesNotExist:
        return Response(
            {"error": "Église non trouvée"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        programme = Programme.objects.get(id=programme_id, church=church)
    except Programme.DoesNotExist:
        return Response(
            {"error": "Programme non trouvé"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    from api.models import ProgrammeContentNotification
    try:
        notification = ProgrammeContentNotification.objects.get(
            id=notification_id,
            programme=programme,
            user=request.user
        )
    except ProgrammeContentNotification.DoesNotExist:
        return Response(
            {"error": "Notification non trouvée"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    from django.utils import timezone
    notification.is_read = True
    notification.read_at = timezone.now()
    notification.save()
    
    from api.serializers import ProgrammeContentNotificationSerializer
    serializer = ProgrammeContentNotificationSerializer(notification)
    return Response(serializer.data)
