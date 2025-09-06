from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db import transaction
from datetime import datetime, date, time, timedelta
import logging

from .models import AttendanceLog
from .serializers import (
    ClockInOutSerializer,
    AttendanceStatusSerializer,
    AttendanceLogSerializer,
    RealTimeAttendanceUpdateSerializer
)
from .face_verification import FaceVerificationService
from students.models import Student
from schedules.models import Schedule
from authentication.models import User

# Import for WebSocket/SSE broadcasting
try:
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    CHANNELS_AVAILABLE = True
except ImportError:
    CHANNELS_AVAILABLE = False

logger = logging.getLogger(__name__)


class ClockInView(APIView):
    """Handle student clock-in with face verification."""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Process clock-in request."""
        # Validate input
        serializer = ClockInOutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'message': 'Invalid input data',
                    'errors': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        snapshot = serializer.validated_data['snapshot']
        schedule_id = serializer.validated_data['schedule_id']
        
        try:
            # Get student from authenticated user
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'message': 'Authenticated user is not a student'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get schedule
        schedule = Schedule.objects.get(id=schedule_id)
        
        # Initialize face verification service
        verification_service = FaceVerificationService()
        
        # Verify face
        verification_result = verification_service.verify_face(
            snapshot_base64=snapshot,
            student_id=student.id
        )
        
        if not verification_result['verified']:
            return Response(
                {
                    'success': False,
                    'status': 'ABSENT',
                    'message': verification_result['message'],
                    'confidence_score': verification_result['confidence']
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Face verified successfully, process clock-in
        current_date = timezone.now().date()
        current_time = timezone.now().time()
        
        with transaction.atomic():
            # Get or create attendance log for today
            attendance_log, created = AttendanceLog.objects.get_or_create(
                student=student,
                schedule=schedule,
                date=current_date,
                defaults={
                    'status': 'PRESENT',
                    'check_in_time': current_time,
                    'face_recognition_confidence': verification_result['confidence']
                }
            )
            
            if not created:
                # Update existing log
                if attendance_log.check_in_time:
                    return Response(
                        {
                            'success': False,
                            'status': attendance_log.status,
                            'message': 'Already clocked in',
                            'check_in_time': attendance_log.check_in_time
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                attendance_log.check_in_time = current_time
                attendance_log.face_recognition_confidence = verification_result['confidence']
                attendance_log.status = 'PRESENT'
            
            # Check if late
            if schedule.start_time:
                check_in_datetime = datetime.combine(date.min, current_time)
                start_datetime = datetime.combine(date.min, schedule.start_time)
                
                # Consider late if more than 10 minutes after start
                if (check_in_datetime - start_datetime).total_seconds() > 600:
                    attendance_log.status = 'LATE'
            
            attendance_log.save()
            
            # Save verification image
            if snapshot:
                snapshot_image = verification_service.decode_base64_image(snapshot)
                image_path = verification_service.save_verification_image(
                    snapshot_image,
                    attendance_log.id,
                    is_clock_in=True
                )
                if image_path:
                    attendance_log.face_image_path = image_path
                    attendance_log.save()
        
        # Broadcast real-time update
        if CHANNELS_AVAILABLE:
            self._broadcast_attendance_update(
                'clock_in',
                attendance_log
            )
        
        # Trigger faculty notification
        try:
            from .pusher_client import trigger_faculty_notification
            trigger_faculty_notification(schedule.id, {
                'type': 'student_clock_in',
                'student_id': student.student_id,
                'student_name': student.user.full_name,
                'status': attendance_log.status,
                'check_in_time': current_time.strftime('%H:%M'),
                'confidence': verification_result['confidence'],
                'timestamp': timezone.now().isoformat(),
            })
        except Exception as e:
            logger.error(f"Failed to send faculty notification: {e}")
        
        # Prepare response
        response_data = {
            'success': True,
            'status': attendance_log.status,
            'message': f'Successfully clocked in at {current_time.strftime("%H:%M:%S")}',
            'student_name': student.user.full_name,
            'course_code': schedule.course_code,
            'check_in_time': current_time,
            'confidence_score': verification_result['confidence'],
            'is_late': attendance_log.status == 'LATE',
            'attendance_log_id': attendance_log.id
        }
        
        return Response(
            response_data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
    
    def _broadcast_attendance_update(self, update_type: str, attendance_log: AttendanceLog):
        """Broadcast attendance update via Pusher Channels."""
        try:
            from .pusher_client import trigger as pusher_trigger

            update_data = RealTimeAttendanceUpdateSerializer({
                'type': update_type,
                'attendance_log': attendance_log,
                'timestamp': timezone.now()
            }).data

            channel = f'attendance-updates-{attendance_log.schedule.id}'
            # Use event name as update type; frontend hook wraps as {type, payload}
            pusher_trigger(channel, update_type, update_data)
        except Exception as e:
            logger.error(f"Error broadcasting attendance update: {str(e)}")


class ClockOutView(APIView):
    """Handle student clock-out with face verification."""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Process clock-out request."""
        # Validate input
        serializer = ClockInOutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'message': 'Invalid input data',
                    'errors': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        snapshot = serializer.validated_data['snapshot']
        schedule_id = serializer.validated_data['schedule_id']
        
        try:
            # Get student from authenticated user
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'message': 'Authenticated user is not a student'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get schedule
        schedule = Schedule.objects.get(id=schedule_id)
        
        # Initialize face verification service
        verification_service = FaceVerificationService()
        
        # Verify face
        verification_result = verification_service.verify_face(
            snapshot_base64=snapshot,
            student_id=student.id
        )
        
        if not verification_result['verified']:
            return Response(
                {
                    'success': False,
                    'message': verification_result['message'],
                    'confidence_score': verification_result['confidence']
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Face verified successfully, process clock-out
        current_date = timezone.now().date()
        current_time = timezone.now().time()
        
        try:
            # Get attendance log for today
            attendance_log = AttendanceLog.objects.get(
                student=student,
                schedule=schedule,
                date=current_date
            )
            
            if not attendance_log.check_in_time:
                return Response(
                    {
                        'success': False,
                        'message': 'Cannot clock out without clocking in first'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if attendance_log.check_out_time:
                return Response(
                    {
                        'success': False,
                        'message': 'Already clocked out',
                        'check_out_time': attendance_log.check_out_time
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update clock-out time
            attendance_log.check_out_time = current_time
            attendance_log.save()
            
            # Save verification image
            if snapshot:
                snapshot_image = verification_service.decode_base64_image(snapshot)
                image_path = verification_service.save_verification_image(
                    snapshot_image,
                    attendance_log.id,
                    is_clock_in=False
                )
            
        except AttendanceLog.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'message': 'No attendance record found for today. Please clock in first.'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Broadcast real-time update
        if CHANNELS_AVAILABLE:
            self._broadcast_attendance_update(
                'clock_out',
                attendance_log
            )
        
        # Prepare response
        response_data = {
            'success': True,
            'status': attendance_log.status,
            'message': f'Successfully clocked out at {current_time.strftime("%H:%M:%S")}',
            'student_name': student.user.full_name,
            'course_code': schedule.course_code,
            'check_in_time': attendance_log.check_in_time,
            'check_out_time': current_time,
            'confidence_score': verification_result['confidence'],
            'attendance_log_id': attendance_log.id
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    def _broadcast_attendance_update(self, update_type: str, attendance_log: AttendanceLog):
        """Broadcast attendance update via Pusher Channels."""
        try:
            from .pusher_client import trigger as pusher_trigger

            update_data = RealTimeAttendanceUpdateSerializer({
                'type': update_type,
                'attendance_log': attendance_log,
                'timestamp': timezone.now()
            }).data

            channel = f'attendance-updates-{attendance_log.schedule.id}'
            pusher_trigger(channel, update_type, update_data)
        except Exception as e:
            logger.error(f"Error broadcasting attendance update: {str(e)}")


class ManualClockInRequestView(APIView):
    """Handle student manual clock-in requests."""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Process manual clock-in request."""
        schedule_id = request.data.get('schedule_id')
        reason = request.data.get('reason', '')
        
        if not schedule_id:
            return Response(
                {
                    'success': False,
                    'message': 'Schedule ID is required'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get student from authenticated user
            student = Student.objects.get(user=request.user)
        except Student.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'message': 'Authenticated user is not a student'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Get schedule
            schedule = Schedule.objects.get(id=schedule_id)
        except Schedule.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'message': 'Schedule not found'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if student is enrolled in this schedule
        if not schedule.groups.filter(students=student).exists():
            return Response(
                {
                    'success': False,
                    'message': 'You are not enrolled in this class'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        current_date = timezone.now().date()
        current_time = timezone.now().time()
        
        # Check if already has attendance for today
        try:
            attendance_log = AttendanceLog.objects.get(
                student=student,
                schedule=schedule,
                date=current_date
            )
            
            if attendance_log.check_in_time:
                return Response(
                    {
                        'success': False,
                        'message': 'Already clocked in for today',
                        'status': attendance_log.status,
                        'check_in_time': attendance_log.check_in_time
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        except AttendanceLog.DoesNotExist:
            pass
        
        # Send manual clock-in request to faculty via Pusher
        try:
            from .pusher_client import trigger_faculty_notification
            
            notification_data = {
                'type': 'manual_clock_in_request',
                'student_id': student.student_id,
                'student_name': student.user.full_name,
                'student_email': student.user.email,
                'schedule_id': schedule.id,
                'course_code': schedule.course_code,
                'course_name': schedule.course_name,
                'reason': reason,
                'request_time': current_time.strftime('%H:%M'),
                'request_date': current_date.isoformat(),
                'timestamp': timezone.now().isoformat(),
            }
            
            success = trigger_faculty_notification(schedule.id, notification_data)
            
            if not success:
                logger.warning(f"Failed to send Pusher notification for manual clock-in request")
            
        except Exception as e:
            logger.error(f"Failed to send faculty notification: {e}")
            return Response(
                {
                    'success': False,
                    'message': 'Failed to send request to lecturer. Please try again.'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response(
            {
                'success': True,
                'message': 'Manual clock-in request sent to lecturer',
                'student_name': student.user.full_name,
                'course_code': schedule.course_code,
                'request_time': current_time.strftime('%H:%M'),
                'reason': reason
            },
            status=status.HTTP_200_OK
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def attendance_status(request, schedule_id):
    """Get current attendance status for a student in a schedule."""
    try:
        # Get student from authenticated user
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return Response(
            {
                'success': False,
                'message': 'Authenticated user is not a student'
            },
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get schedule
    try:
        schedule = Schedule.objects.get(id=schedule_id)
    except Schedule.DoesNotExist:
        return Response(
            {
                'success': False,
                'message': 'Schedule not found'
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get attendance log for today
    current_date = timezone.now().date()
    
    try:
        attendance_log = AttendanceLog.objects.get(
            student=student,
            schedule=schedule,
            date=current_date
        )
        
        serializer = AttendanceLogSerializer(attendance_log)
        
        return Response(
            {
                'success': True,
                'has_attendance': True,
                'attendance': serializer.data
            },
            status=status.HTTP_200_OK
        )
    
    except AttendanceLog.DoesNotExist:
        return Response(
            {
                'success': True,
                'has_attendance': False,
                'message': 'No attendance record for today'
            },
            status=status.HTTP_200_OK
        )
