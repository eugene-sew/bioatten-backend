from django.db import models
from common.models import BaseModel
from students.models import Student
from schedules.models import Schedule


class AttendanceLog(BaseModel):
    """Model representing student attendance for a scheduled class."""
    
    ATTENDANCE_STATUS_CHOICES = [
        ('PRESENT', 'Present'),
        ('ABSENT', 'Absent'),
        ('LATE', 'Late'),
        ('EXCUSED', 'Excused'),
    ]
    
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name='attendance_logs'
    )
    schedule = models.ForeignKey(
        Schedule,
        on_delete=models.CASCADE,
        related_name='attendance_logs'
    )
    date = models.DateField(db_index=True)
    status = models.CharField(
        max_length=10,
        choices=ATTENDANCE_STATUS_CHOICES,
        default='ABSENT',
        db_index=True
    )
    check_in_time = models.TimeField(null=True, blank=True)
    check_out_time = models.TimeField(null=True, blank=True)
    
    # Facial recognition related fields
    face_recognition_confidence = models.FloatField(null=True, blank=True)
    face_image_path = models.CharField(max_length=500, blank=True)
    
    # Manual override fields
    is_manual_override = models.BooleanField(default=False)
    override_reason = models.TextField(blank=True)
    override_by = models.ForeignKey(
        'authentication.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attendance_overrides'
    )
    
    class Meta:
        db_table = 'attendance_logs'
        verbose_name = 'Attendance Log'
        verbose_name_plural = 'Attendance Logs'
        ordering = ['-date', 'schedule__start_time']
        unique_together = [['student', 'schedule', 'date']]
    
    def __str__(self):
        return f"{self.student} - {self.schedule.course_code} - {self.date} ({self.get_status_display()})"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        if self.check_out_time and not self.check_in_time:
            raise ValidationError("Check-out time cannot be set without check-in time.")
        
        if self.check_in_time and self.check_out_time:
            if self.check_in_time >= self.check_out_time:
                raise ValidationError("Check-out time must be after check-in time.")
    
    @property
    def is_late(self):
        """Check if the student was late based on check-in time."""
        if self.check_in_time and self.schedule.start_time:
            # Convert times to comparable format
            from datetime import datetime, date
            check_in = datetime.combine(date.min, self.check_in_time)
            start = datetime.combine(date.min, self.schedule.start_time)
            
            # Consider late if checked in more than 10 minutes after start
            return (check_in - start).total_seconds() > 600
        return False
