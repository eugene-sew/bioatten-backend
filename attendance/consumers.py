import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from authentication.models import User
from schedules.models import Schedule
import logging

logger = logging.getLogger(__name__)


class AttendanceUpdateConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time attendance updates."""
    
    async def connect(self):
        """Handle WebSocket connection."""
        # Get schedule ID from URL route
        self.schedule_id = self.scope['url_route']['kwargs'].get('schedule_id')
        self.room_group_name = f'attendance_updates_{self.schedule_id}'
        
        # Check authentication
        user = self.scope.get('user', AnonymousUser())
        
        if isinstance(user, AnonymousUser):
            # Reject connection if not authenticated
            await self.close()
            return
        
        # Check if user has permission to view attendance updates
        has_permission = await self.check_user_permission(user, self.schedule_id)
        
        if not has_permission:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': f'Connected to attendance updates for schedule {self.schedule_id}'
        }))
        
        logger.info(f"WebSocket connected: user={user.email}, schedule={self.schedule_id}")
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Leave room group
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        
        logger.info(f"WebSocket disconnected: schedule={self.schedule_id}, code={close_code}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'ping':
                # Respond to ping with pong
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))
            
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON data'
            }))
    
    async def attendance_update(self, event):
        """Handle attendance update from channel layer."""
        # Send update to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'attendance_update',
            'data': event['data']
        }))
    
    @database_sync_to_async
    def check_user_permission(self, user: User, schedule_id: int) -> bool:
        """Check if user has permission to view attendance updates."""
        # Admin users can view all attendance updates
        if user.is_staff or user.is_superuser:
            return True
        
        # Faculty can view attendance for their courses
        if user.role == 'FACULTY':
            try:
                schedule = Schedule.objects.get(id=schedule_id)
                return schedule.faculty.user == user
            except Schedule.DoesNotExist:
                return False
        
        # Students can view their own attendance
        if user.role == 'STUDENT':
            return True  # Further filtering will be done in views
        
        return False
