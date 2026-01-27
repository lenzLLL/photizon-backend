from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db.models import Q

from api.models import ChatRoom, ChatMessage, Church, ChurchAdmin, Commission
from api.serializers import ChatRoomSerializer, ChatRoomCreateUpdateSerializer, ChatMessageSerializer
from api.permissions import IsAuthenticatedUser


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticatedUser])
def list_create_chat_rooms(request, church_id):
    """List all chat rooms for a church or create a new one"""
    user = request.user
    
    # Check user has access to this church
    church = get_object_or_404(Church, id=church_id)
    
    # Check if user is admin of this church
    is_admin = ChurchAdmin.objects.filter(
        user=user,
        church=church,
        role__in=['OWNER', 'ADMIN']
    ).exists()
    
    if not is_admin and user.role != 'SADMIN':
        return Response(
            {"error": "You don't have access to this church"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if request.method == 'GET':
        rooms = ChatRoom.objects.filter(church=church).prefetch_related('messages')
        serializer = ChatRoomSerializer(rooms, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        data = request.data.copy()
        data['church'] = church_id
        data['created_by'] = user.id
        
        serializer = ChatRoomCreateUpdateSerializer(data=data)
        if serializer.is_valid():
            serializer.save(created_by=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticatedUser])
def room_detail(request, room_id):
    """Get, update or delete a chat room"""
    user = request.user
    room = get_object_or_404(ChatRoom, id=room_id)
    
    # Check if user has access
    if not room.user_has_access(user) and user.role != 'SADMIN':
        return Response(
            {"error": "You don't have access to this room"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Only admins can update/delete
    is_admin = ChurchAdmin.objects.filter(
        user=user,
        church=room.church,
        role__in=['OWNER', 'ADMIN']
    ).exists() or user.role == 'SADMIN'
    
    if request.method == 'GET':
        serializer = ChatRoomSerializer(room)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        if not is_admin:
            return Response(
                {"error": "Only admins can update rooms"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ChatRoomCreateUpdateSerializer(room, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        if not is_admin:
            return Response(
                {"error": "Only admins can delete rooms"},
                status=status.HTTP_403_FORBIDDEN
            )
        room.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticatedUser])
def list_create_messages(request, room_id):
    """List all messages in a room or post a new message"""
    user = request.user
    room = get_object_or_404(ChatRoom, id=room_id)
    
    # Check if user has access
    if not room.user_has_access(user):
        return Response(
            {"error": "You don't have access to this room"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if request.method == 'GET':
        messages = room.messages.all()
        
        # Optional: limit to last N messages
        limit = request.GET.get('limit', 50)
        try:
            limit = int(limit)
            messages = messages[:limit]
        except ValueError:
            pass
        
        serializer = ChatMessageSerializer(messages, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        data = request.data.copy()
        data['room'] = room_id
        data['user'] = user.id
        
        serializer = ChatMessageSerializer(data=data)
        if serializer.is_valid():
            serializer.save(room=room, user=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticatedUser])
def message_detail(request, room_id, message_id):
    """Get, update or delete a message"""
    user = request.user
    
    room = get_object_or_404(ChatRoom, id=room_id)
    message = get_object_or_404(ChatMessage, id=message_id, room=room)
    
    # Check if user has access to room
    if not room.user_has_access(user):
        return Response(
            {"error": "You don't have access to this room"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    if request.method == 'GET':
        serializer = ChatMessageSerializer(message)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        # Only message author can update
        if message.user_id != user.id and user.role != 'SADMIN':
            return Response(
                {"error": "You can only edit your own messages"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ChatMessageSerializer(message, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Only message author or admins can delete
        is_owner = message.user_id == user.id
        is_admin = ChurchAdmin.objects.filter(
            user=user,
            church=room.church,
            role__in=['OWNER', 'ADMIN']
        ).exists() or user.role == 'SADMIN'
        
        if not (is_owner or is_admin):
            return Response(
                {"error": "You can only delete your own messages"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        message.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticatedUser])
def add_member_to_custom_room(request, room_id):
    """Add members to a custom chat room"""
    user = request.user
    room = get_object_or_404(ChatRoom, id=room_id)
    
    if room.room_type != 'CUSTOM':
        return Response(
            {"error": "Only CUSTOM rooms support adding members"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if user is admin
    is_admin = ChurchAdmin.objects.filter(
        user=user,
        church=room.church,
        role__in=['OWNER', 'ADMIN']
    ).exists() or user.role == 'SADMIN'
    
    if not is_admin:
        return Response(
            {"error": "Only admins can add members"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    user_ids = request.data.get('user_ids', [])
    if not user_ids:
        return Response(
            {"error": "user_ids is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Add users to room
    for uid in user_ids:
        room.members.add(uid)
    
    return Response(
        {"message": f"Added {len(user_ids)} members"},
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([IsAuthenticatedUser])
def remove_member_from_custom_room(request, room_id):
    """Remove members from a custom chat room"""
    user = request.user
    room = get_object_or_404(ChatRoom, id=room_id)
    
    if room.room_type != 'CUSTOM':
        return Response(
            {"error": "Only CUSTOM rooms support removing members"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if user is admin
    is_admin = ChurchAdmin.objects.filter(
        user=user,
        church=room.church,
        role__in=['OWNER', 'ADMIN']
    ).exists() or user.role == 'SADMIN'
    
    if not is_admin:
        return Response(
            {"error": "Only admins can remove members"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    user_ids = request.data.get('user_ids', [])
    if not user_ids:
        return Response(
            {"error": "user_ids is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Remove users from room
    for uid in user_ids:
        room.members.remove(uid)
    
    return Response(
        {"message": f"Removed {len(user_ids)} members"},
        status=status.HTTP_200_OK
    )


# =====================================================
# Programme Chat Endpoints
# =====================================================

@api_view(['POST'])
@permission_classes([IsAuthenticatedUser])
def create_programme_chat(request, church_id, programme_id):
    """
    Créer un chat pour un programme
    Body: {
        "name": "string (optionnel)"
    }
    """
    from api.models import Programme
    from api.permissions import is_church_admin
    
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
    if not is_church_admin(request.user, church) and request.user.role != "SADMIN":
        return Response(
            {"error": "Vous devez être administrateur de cette église"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Vérifier qu'un chat n'existe pas déjà pour ce programme
    existing = ChatRoom.objects.filter(programme=programme, room_type='PROGRAMME').first()
    if existing:
        return Response(
            {"error": "Un chat existe déjà pour ce programme"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    name = request.data.get('name') or f"Chat - {programme.title}"
    
    chat_room = ChatRoom.objects.create(
        church=church,
        programme=programme,
        room_type='PROGRAMME',
        name=name,
        created_by=request.user
    )
    
    serializer = ChatRoomSerializer(chat_room)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticatedUser])
def get_programme_chat(request, church_id, programme_id):
    """
    Récupérer le chat d'un programme
    """
    from api.models import Programme
    
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
    if request.user.current_church_id != church.id and request.user.role != "SADMIN":
        return Response(
            {"error": "Vous devez être membre de cette église"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    chat_room = ChatRoom.objects.filter(
        programme=programme,
        room_type='PROGRAMME'
    ).first()
    
    if not chat_room:
        return Response(
            {"error": "Aucun chat pour ce programme"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = ChatRoomSerializer(chat_room)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticatedUser])
def send_programme_message(request, church_id, programme_id):
    """
    Envoyer un message dans le chat du programme
    Body: {
        "content": "string"
    }
    """
    from api.models import Programme
    
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
    if request.user.current_church_id != church.id and request.user.role != "SADMIN":
        return Response(
            {"error": "Vous devez être membre de cette église"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    chat_room = ChatRoom.objects.filter(
        programme=programme,
        room_type='PROGRAMME'
    ).first()
    
    if not chat_room:
        return Response(
            {"error": "Aucun chat pour ce programme"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    content = request.data.get('content')
    if not content:
        return Response(
            {"error": "content requis"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    message = ChatMessage.objects.create(
        room=chat_room,
        user=request.user,
        content=content
    )
    
    serializer = ChatMessageSerializer(message)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticatedUser])
def get_programme_messages(request, church_id, programme_id):
    """
    Récupérer les messages du chat d'un programme
    Query params: limit, offset
    """
    from api.models import Programme
    
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
    if request.user.current_church_id != church.id and request.user.role != "SADMIN":
        return Response(
            {"error": "Vous devez être membre de cette église"},
            status=status.HTTP_403_FORBIDDEN
        )
    
    chat_room = ChatRoom.objects.filter(
        programme=programme,
        room_type='PROGRAMME'
    ).first()
    
    if not chat_room:
        return Response(
            {"error": "Aucun chat pour ce programme"},
            status=status.HTTP_404_NOT_FOUND
        )
    
    messages = ChatMessage.objects.filter(room=chat_room).select_related(
        'user'
    ).order_by('-created_at')
    
    # Pagination
    try:
        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))
    except ValueError:
        limit = 20
        offset = 0
    
    limit = min(limit, 100)
    total_count = messages.count()
    paginated_messages = messages[offset:offset + limit]
    
    serializer = ChatMessageSerializer(paginated_messages, many=True)
    
    return Response({
        "count": total_count,
        "limit": limit,
        "offset": offset,
        "next_offset": offset + limit if offset + limit < total_count else None,
        "results": serializer.data
    })
