from rest_framework import serializers
from .models import AttendanceLog, ManualClockInRequest
from students.models import Student
from schedules.models import Schedule
from facial_recognition.models import FacialEnrollment
import base64
import numpy as np


class ClockInOutSerializer(serializers.Serializer):
    """Serializer for clock-in/clock-out requests."""
    
    snapshot = serializers.CharField(
        help_text="Base64 encoded image snapshot from the student"
    )
    schedule_id = serializers.IntegerField(
        help_text="ID of the schedule to clock in/out for"
    )
    
    def validate_snapshot(self, value):
        """Validate that the snapshot is a valid base64 image."""
        try:
            # Check if it's a data URL
            if value.startswith('data:image'):
                # Extract base64 part
                value = value.split(',')[1]
            
            # Try to decode
            base64.b64decode(value)
            return value
        except Exception as e:
            raise serializers.ValidationError(f"Invalid image data: {str(e)}")
    
    def validate_schedule_id(self, value):
        """Validate that the schedule exists."""
        try:
            Schedule.objects.get(id=value)
            return value
        except Schedule.DoesNotExist:
            raise serializers.ValidationError("Schedule not found")


class AttendanceStatusSerializer(serializers.Serializer):
    """Serializer for attendance status response."""
    
    success = serializers.BooleanField()
    status = serializers.ChoiceField(choices=AttendanceLog.ATTENDANCE_STATUS_CHOICES)
    message = serializers.CharField()
    student_name = serializers.CharField(required=False)
    course_code = serializers.CharField(required=False)
    check_in_time = serializers.TimeField(required=False)
    check_out_time = serializers.TimeField(required=False)
    confidence_score = serializers.FloatField(required=False)
    is_late = serializers.BooleanField(required=False)
    attendance_log_id = serializers.IntegerField(required=False)


class AttendanceLogSerializer(serializers.ModelSerializer):
    """Serializer for AttendanceLog model."""
    
    student_name = serializers.CharField(source='student.user.full_name', read_only=True)
    student_id = serializers.CharField(source='student.student_id', read_only=True)
    course_code = serializers.CharField(source='schedule.course_code', read_only=True)
    course_name = serializers.CharField(source='schedule.course_name', read_only=True)
    
    class Meta:
        model = AttendanceLog
        fields = [
            'id', 'student', 'student_name', 'student_id',
            'schedule', 'course_code', 'course_name',
            'date', 'status', 'check_in_time', 'check_out_time',
            'face_recognition_confidence', 'is_late',
            'is_manual_override', 'override_reason', 'created_at'
        ]
        read_only_fields = ['is_late', 'created_at']


class RealTimeAttendanceUpdateSerializer(serializers.Serializer):
    """Serializer for real-time attendance updates via WebSocket/SSE."""
    
    type = serializers.ChoiceField(choices=['clock_in', 'clock_out', 'status_change'])
    attendance_log = AttendanceLogSerializer()
    timestamp = serializers.DateTimeField()


class ManualClockInRequestSerializer(serializers.ModelSerializer):
    """Serializer for ManualClockInRequest model."""
    
    student_name = serializers.CharField(source='student.user.full_name', read_only=True)
    student_id = serializers.CharField(source='student.student_id', read_only=True)
    student_email = serializers.CharField(source='student.user.email', read_only=True)
    course_name = serializers.CharField(source='schedule.title', read_only=True)
    course_code = serializers.CharField(source='schedule.course_code', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.full_name', read_only=True)
    
    class Meta:
        model = ManualClockInRequest
        fields = [
            'id', 'student', 'student_name', 'student_id', 'student_email',
            'schedule', 'course_name', 'course_code', 'attendance_date',
            'reason', 'status', 'priority', 'reviewed_by', 'reviewed_by_name',
            'admin_response', 'reviewed_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['student', 'schedule', 'created_at', 'updated_at']


class ManualRequestActionSerializer(serializers.Serializer):
    """Serializer for approve/reject manual request actions."""
    
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)
