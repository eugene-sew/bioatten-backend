import json
import time
from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from schedules.models import Schedule
from .models import AttendanceLog
from .serializers import AttendanceLogSerializer
import logging

logger = logging.getLogger(__name__)


def attendance_updates_sse(request, schedule_id):
    """
    Server-Sent Events endpoint for real-time attendance updates.
    
    This provides a simpler alternative to WebSockets for real-time updates.
    """
    # Check authentication
    if not request.user.is_authenticated:
        return StreamingHttpResponse(
            "data: {\"error\": \"Authentication required\"}\n\n",
            content_type='text/event-stream',
            status=401
        )
    
    # Check permissions
    user = request.user
    try:
        schedule = Schedule.objects.get(id=schedule_id)
        
        # Check if user has permission to view attendance
        if not (user.is_staff or user.is_superuser):
            if user.role == 'FACULTY' and schedule.faculty.user != user:
                return StreamingHttpResponse(
                    "data: {\"error\": \"Permission denied\"}\n\n",
                    content_type='text/event-stream',
                    status=403
                )
    except Schedule.DoesNotExist:
        return StreamingHttpResponse(
            "data: {\"error\": \"Schedule not found\"}\n\n",
            content_type='text/event-stream',
            status=404
        )
    
    def event_stream():
        """Generate SSE events."""
        # Send initial connection message
        yield f"data: {json.dumps({'type': 'connected', 'schedule_id': schedule_id})}\n\n"
        
        # Track last update time
        last_update = timezone.now()
        
        while True:
            try:
                # Get recent attendance updates
                recent_logs = AttendanceLog.objects.filter(
                    schedule_id=schedule_id,
                    updated_at__gt=last_update
                ).select_related('student__user', 'schedule')
                
                for log in recent_logs:
                    # Determine update type
                    if log.created_at > last_update:
                        update_type = 'clock_in'
                    elif log.check_out_time and log.updated_at > last_update:
                        update_type = 'clock_out'
                    else:
                        update_type = 'status_change'
                    
                    # Serialize attendance log
                    serializer = AttendanceLogSerializer(log)
                    
                    # Create event data
                    event_data = {
                        'type': update_type,
                        'attendance_log': serializer.data,
                        'timestamp': timezone.now().isoformat()
                    }
                    
                    # Send SSE event
                    yield f"data: {json.dumps(event_data)}\n\n"
                
                # Update last check time
                if recent_logs:
                    last_update = timezone.now()
                
                # Send heartbeat to keep connection alive
                yield f": heartbeat\n\n"
                
                # Sleep for a short interval
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error in SSE stream: {str(e)}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                break
    
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    
    # Disable caching
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test_attendance_broadcast(request, schedule_id):
    """Test endpoint to trigger an attendance update broadcast."""
    from django.utils import timezone
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    
    # This is just for testing the broadcast functionality
    test_data = {
        'type': 'test_update',
        'message': f'Test broadcast at {timezone.now().isoformat()}',
        'schedule_id': schedule_id
    }
    
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'attendance_updates_{schedule_id}',
            {
                'type': 'attendance_update',
                'data': test_data
            }
        )
        
        return StreamingHttpResponse(
            json.dumps({
                'success': True,
                'message': 'Test broadcast sent',
                'data': test_data
            }),
            content_type='application/json'
        )
    except Exception as e:
        return StreamingHttpResponse(
            json.dumps({
                'success': False,
                'message': f'Failed to send broadcast: {str(e)}'
            }),
            content_type='application/json',
            status=500
        )
