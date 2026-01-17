import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatMessage, ChatRoom
from .serializers import ChatMessageSerializer


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time chat"""

    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']

        # Verify user has access to this room
        has_access = await self.check_room_access()
        if not has_access:
            await self.close()
            return

        # Add to group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Remove from group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Receive message from WebSocket"""
        try:
            data = json.loads(text_data)
            message_text = data.get('message', '').strip()

            if not message_text:
                return

            # Save message to database
            message_obj = await self.save_message(message_text)

            # Broadcast to group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message_id': str(message_obj.id),
                    'user_id': str(self.user.id),
                    'user_name': self.user.name,
                    'message': message_text,
                    'created_at': message_obj.created_at.isoformat(),
                }
            )
        except json.JSONDecodeError:
            pass

    async def chat_message(self, event):
        """Handle chat message event"""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'id': event['message_id'],
            'user_id': event['user_id'],
            'user_name': event['user_name'],
            'message': event['message'],
            'created_at': event['created_at'],
        }))

    @database_sync_to_async
    def save_message(self, message_text):
        """Save message to database"""
        room = ChatRoom.objects.get(id=self.room_id)
        message = ChatMessage.objects.create(
            room=room,
            user=self.user,
            message=message_text
        )
        return message

    @database_sync_to_async
    def check_room_access(self):
        """Check if user has access to this room based on room_type"""
        if not self.user.is_authenticated:
            return False

        try:
            room = ChatRoom.objects.get(id=self.room_id)
            return room.user_has_access(self.user)
        except ChatRoom.DoesNotExist:
            return False
