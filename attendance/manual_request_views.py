from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Count
from datetime import datetime, date, timedelta
import logging

from .models import ManualClockInRequest, AttendanceLog
from .serializers import ManualClockInRequestSerializer, ManualRequestActionSerializer
from students.models import Student
from schedules.models import Schedule
from authentication.models import User
from faculty.models import Faculty

logger = logging.getLogger(__name__)


class ManualRequestsListView(APIView):
    """Handle listing and filtering manual clock-in requests."""
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get manual requests with filtering and statistics."""
        user = request.user
        status_filter = request.GET.get('status', 'pending')
        
        # Base queryset - filter by user role
        if hasattr(user, 'faculty_profile'):
            # Faculty can only see requests for their schedules
            faculty = user.faculty_profile
            base_queryset = ManualClockInRequest.objects.filter(
                schedule__faculty=faculty
            )
        elif user.role == 'ADMIN':
            # Admin can see all requests
            base_queryset = ManualClockInRequest.objects.all()
        else:
            # Students can only see their own requests
            try:
                student = Student.objects.get(user=user)
                base_queryset = ManualClockInRequest.objects.filter(student=student)
            except Student.DoesNotExist:
                return Response(
                    {'success': False, 'message': 'Access denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Apply status filter
        if status_filter != 'all':
            queryset = base_queryset.filter(status=status_filter)
        else:
            queryset = base_queryset
        
        # Get statistics
        today = timezone.now().date()
        stats = {
            'pending': base_queryset.filter(status='pending').count(),
            'approved_today': base_queryset.filter(
                status='approved',
                reviewed_at__date=today
            ).count(),
            'rejected_today': base_queryset.filter(
                status='rejected',
                reviewed_at__date=today
            ).count(),
            'total': base_queryset.count()
        }
        
        # Order and serialize requests
        requests = queryset.select_related(
            'student__user', 'schedule', 'reviewed_by'
        ).order_by('-created_at')
        
        serializer = ManualClockInRequestSerializer(requests, many=True)
        
        return Response({
            'success': True,
            'requests': serializer.data,
            'stats': stats
        }, status=status.HTTP_200_OK)


class ManualRequestActionView(APIView):
    """Handle approve/reject actions for manual requests."""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request, request_id, action):
        """Approve or reject a manual request."""
        if action not in ['approve', 'reject']:
            return Response(
                {'success': False, 'message': 'Invalid action'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate request data
        serializer = ManualRequestActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'success': False, 'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        admin_reason = serializer.validated_data.get('reason', '')
        
        try:
            manual_request = ManualClockInRequest.objects.select_related(
                'student', 'schedule'
            ).get(id=request_id)
        except ManualClockInRequest.DoesNotExist:
            return Response(
                {'success': False, 'message': 'Request not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permissions
        user = request.user
        if hasattr(user, 'faculty_profile'):
            # Faculty can only approve/reject requests for their schedules
            if manual_request.schedule.faculty != user.faculty_profile:
                return Response(
                    {'success': False, 'message': 'Access denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
        elif user.role != 'ADMIN':
            return Response(
                {'success': False, 'message': 'Access denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if already processed
        if manual_request.status != 'pending':
            return Response(
                {'success': False, 'message': f'Request already {manual_request.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # Update request status
            manual_request.status = 'approved' if action == 'approve' else 'rejected'
            manual_request.reviewed_by = user
            manual_request.admin_response = admin_reason
            manual_request.reviewed_at = timezone.now()
            manual_request.save()
            
            # If approved, create attendance log
            if action == 'approve':
                attendance_log, created = AttendanceLog.objects.get_or_create(
                    student=manual_request.student,
                    schedule=manual_request.schedule,
                    date=manual_request.attendance_date,
                    defaults={
                        'status': 'PRESENT',
                        'check_in_time': manual_request.schedule.start_time,
                        'is_manual_override': True,
                        'override_reason': f"Manual request approved: {manual_request.reason}",
                        'override_by': user
                    }
                )
                
                if not created and not attendance_log.check_in_time:
                    # Update existing log if no check-in time
                    attendance_log.status = 'PRESENT'
                    attendance_log.check_in_time = manual_request.schedule.start_time
                    attendance_log.is_manual_override = True
                    attendance_log.override_reason = f"Manual request approved: {manual_request.reason}"
                    attendance_log.override_by = user
                    attendance_log.save()
            
            # Send notification about the decision
            try:
                from .pusher_client import trigger
                
                notification_data = {
                    'type': 'manual_request_decision',
                    'request_id': manual_request.id,
                    'student_id': manual_request.student.student_id,
                    'student_name': manual_request.student.user.full_name,
                    'course_name': manual_request.schedule.title,
                    'action': action,
                    'status': manual_request.status,
                    'admin_response': admin_reason,
                    'reviewed_by': user.full_name,
                    'timestamp': timezone.now().isoformat(),
                }
                
                # Send to faculty channel
                faculty_channel = f'faculty-{manual_request.schedule.faculty.id}'
                trigger(faculty_channel, 'attendance-notification', notification_data)
                
                # Send to student channel
                student_channel = f'student-{manual_request.student.id}'
                trigger(student_channel, 'attendance-notification', notification_data)
                
            except Exception as e:
                logger.error(f"Failed to send decision notification: {e}")
        
        action_text = 'approved' if action == 'approve' else 'rejected'
        return Response({
            'success': True,
            'message': f'Request {action_text} successfully',
            'request_id': manual_request.id,
            'status': manual_request.status
        }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_manual_requests(request):
    """Get manual requests - wrapper for compatibility."""
    view = ManualRequestsListView()
    return view.get(request)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_manual_request(request, request_id):
    """Approve a manual request - wrapper for compatibility."""
    view = ManualRequestActionView()
    return view.post(request, request_id, 'approve')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_manual_request(request, request_id):
    """Reject a manual request - wrapper for compatibility."""
    view = ManualRequestActionView()
    return view.post(request, request_id, 'reject')
