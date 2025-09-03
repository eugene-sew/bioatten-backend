from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from datetime import date, datetime, time

from .models import AttendanceLog
from .serializers import AttendanceLogSerializer
from students.models import Student
from schedules.models import Schedule
from authentication.permissions import IsFaculty, IsAdminOrFaculty
from .pusher_client import trigger_attendance_update

import logging
logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminOrFaculty])
def get_schedule_attendance(request, schedule_id):
    """Get attendance records for a specific schedule."""
    schedule = get_object_or_404(Schedule, id=schedule_id)
    
    # Check if faculty owns this schedule
    if hasattr(request.user, 'faculty_profile'):
        if schedule.faculty != request.user.faculty_profile:
            return Response(
                {'error': 'You do not have permission to view this schedule'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    # Get today's date or specified date
    target_date = request.GET.get('date', str(date.today()))
    
    # Get all students in the assigned group
    group_students = Student.objects.filter(
        group=schedule.assigned_group,
        status='ACTIVE'
    ).select_related('user')
    
    # Get existing attendance records
    attendance_records = AttendanceLog.objects.filter(
        schedule=schedule,
        date=target_date
    ).select_related('student__user')
    
    # Create attendance data with all students
    attendance_data = []
    for student in group_students:
        # Find existing record
        record = next(
            (r for r in attendance_records if r.student_id == student.id),
            None
        )
        
        if record:
            attendance_data.append({
                'id': record.id,
                'student_id': student.student_id,
                'student_name': student.user.full_name,
                'status': record.status,
                'check_in_time': record.check_in_time.strftime('%H:%M') if record.check_in_time else None,
                'check_out_time': record.check_out_time.strftime('%H:%M') if record.check_out_time else None,
                'is_manual_override': record.is_manual_override,
                'face_recognition_confidence': record.face_recognition_confidence,
            })
        else:
            # Student not yet marked
            attendance_data.append({
                'id': None,
                'student_id': student.student_id,
                'student_name': student.user.full_name,
                'status': 'ABSENT',
                'check_in_time': None,
                'check_out_time': None,
                'is_manual_override': False,
                'face_recognition_confidence': None,
            })
    
    return Response({
        'schedule': {
            'id': schedule.id,
            'title': schedule.title,
            'course_code': schedule.course_code,
            'date': target_date,
            'start_time': schedule.start_time.strftime('%H:%M') if schedule.start_time else None,
            'end_time': schedule.end_time.strftime('%H:%M') if schedule.end_time else None,
        },
        'attendance': attendance_data,
        'stats': {
            'total': len(group_students),
            'present': len([r for r in attendance_data if r['status'] == 'PRESENT']),
            'late': len([r for r in attendance_data if r['status'] == 'LATE']),
            'absent': len([r for r in attendance_data if r['status'] == 'ABSENT']),
        }
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminOrFaculty])
def manual_clock_in(request, schedule_id):
    """Manually clock in a student."""
    schedule = get_object_or_404(Schedule, id=schedule_id)
    
    # Check permissions
    if hasattr(request.user, 'faculty_profile'):
        if schedule.faculty != request.user.faculty_profile:
            return Response(
                {'error': 'You do not have permission to modify this schedule'},
                status=status.HTTP_403_FORBIDDEN
            )
    
    student_id = request.data.get('student_id')
    if not student_id:
        return Response(
            {'error': 'student_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        student = Student.objects.get(student_id=student_id)
    except Student.DoesNotExist:
        return Response(
            {'error': 'Student not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if student is in the assigned group
    if student.group != schedule.assigned_group:
        return Response(
            {'error': 'Student is not in the assigned group for this schedule'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    target_date = request.data.get('date', str(date.today()))
    current_time = timezone.now().time()
    
    with transaction.atomic():
        # Get or create attendance record
        attendance_log, created = AttendanceLog.objects.get_or_create(
            student=student,
            schedule=schedule,
            date=target_date,
            defaults={
                'status': 'PRESENT',
                'check_in_time': current_time,
                'is_manual_override': True,
                'override_reason': f'Manually clocked in by {request.user.full_name}',
                'override_by': request.user,
            }
        )
        
        if not created and attendance_log.check_in_time:
            return Response(
                {'error': 'Student already clocked in'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not created:
            attendance_log.check_in_time = current_time
            attendance_log.status = 'PRESENT'
            attendance_log.is_manual_override = True
            attendance_log.override_reason = f'Manually clocked in by {request.user.full_name}'
            attendance_log.override_by = request.user
        
        # Check if late
        if schedule.start_time:
            check_in_datetime = datetime.combine(date.min, current_time)
            start_datetime = datetime.combine(date.min, schedule.start_time)
            
            if (check_in_datetime - start_datetime).total_seconds() > 600:  # 10 minutes
                attendance_log.status = 'LATE'
        
        attendance_log.save()
    
    # Trigger Pusher notification
    try:
        trigger_attendance_update(schedule_id, {
            'type': 'manual_clock_in',
            'student_id': student.student_id,
            'student_name': student.user.full_name,
            'status': attendance_log.status,
            'check_in_time': attendance_log.check_in_time.strftime('%H:%M'),
            'faculty_name': request.user.full_name,
        })
    except Exception as e:
        logger.error(f"Failed to send Pusher notification: {e}")
    
    return Response({
        'success': True,
        'message': f'{student.user.full_name} has been manually clocked in',
        'attendance': {
            'student_id': student.student_id,
            'student_name': student.user.full_name,
            'status': attendance_log.status,
            'check_in_time': attendance_log.check_in_time.strftime('%H:%M'),
            'is_manual_override': True,
        }
    })
