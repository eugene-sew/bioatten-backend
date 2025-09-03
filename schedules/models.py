from django.db import models
from django.core.exceptions import ValidationError
from common.models import BaseModel
from students.models import StudentGroup
from faculty.models import Faculty


class Schedule(BaseModel):
    """Model representing a class schedule."""
    
    title = models.CharField(max_length=200, help_text="Title or name of the class session")
    course_code = models.CharField(max_length=20, db_index=True)
    date = models.DateField(db_index=True, help_text="Date of the scheduled class")
    start_time = models.TimeField(help_text="Class start time")
    end_time = models.TimeField(help_text="Class end time")
    
    # Clock-in time windows
    clock_in_opens_at = models.TimeField(
        help_text="Time when students can start clocking in (e.g., 15 minutes before start)"
    )
    clock_in_closes_at = models.TimeField(
        help_text="Time when clock-in window closes (e.g., 15 minutes after start)"
    )
    
    # Relationships
    assigned_group = models.ForeignKey(
        StudentGroup,
        on_delete=models.CASCADE,
        related_name='schedules',
        help_text="Student group assigned to this class"
    )
    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='schedules',
        help_text="Faculty member teaching this class"
    )
    
    # Optional fields
    room = models.CharField(max_length=50, blank=True, help_text="Room or location (legacy)")
    location = models.CharField(max_length=100, blank=True, help_text="Display location for frontend")
    description = models.TextField(blank=True, help_text="Additional notes or description")
    is_active = models.BooleanField(default=True, db_index=True)

    # Recurrence fields to align with frontend form
    recurring = models.BooleanField(default=False, help_text="Whether this schedule recurs")
    recurrence_pattern = models.CharField(
        max_length=10,
        choices=[('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly')],
        default='weekly',
        help_text="Pattern for recurrence when recurring is true"
    )
    recurrence_end_date = models.DateField(null=True, blank=True, help_text="End date for recurrence")
    days_of_week = models.JSONField(default=list, blank=True, help_text="List of weekday numbers 0-6 for weekly pattern")
    
    class Meta:
        db_table = 'schedules'
        verbose_name = 'Schedule'
        verbose_name_plural = 'Schedules'
        ordering = ['date', 'start_time']
        indexes = [
            models.Index(fields=['date', 'assigned_group']),
            models.Index(fields=['date', 'faculty']),
        ]
        # Prevent double-booking
        unique_together = [
            ['assigned_group', 'date', 'start_time'],
            ['faculty', 'date', 'start_time'],
        ]
    
    def __str__(self):
        return f"{self.title} - {self.course_code} ({self.date} {self.start_time}-{self.end_time})"
    
    def clean(self):
        """Validate the schedule data."""
        errors = {}
        
        # Validate time order
        if self.start_time >= self.end_time:
            errors['end_time'] = "End time must be after start time."
        
        # Validate clock-in window
        if self.clock_in_opens_at > self.start_time:
            errors['clock_in_opens_at'] = "Clock-in cannot open after the class starts."
        
        if self.clock_in_closes_at < self.start_time:
            errors['clock_in_closes_at'] = "Clock-in cannot close before the class starts."
        
        if self.clock_in_opens_at >= self.clock_in_closes_at:
            errors['clock_in_closes_at'] = "Clock-in close time must be after open time."
        
        # Validate clock-in window is within reasonable bounds
        # (e.g., opens max 1 hour before, closes max 1 hour after start)
        from datetime import datetime, timedelta
        
        # Convert times to datetime for calculation
        dummy_date = datetime(2000, 1, 1)
        start_dt = datetime.combine(dummy_date, self.start_time)
        open_dt = datetime.combine(dummy_date, self.clock_in_opens_at)
        close_dt = datetime.combine(dummy_date, self.clock_in_closes_at)
        
        # Check if clock-in opens too early (more than 1 hour before start)
        if (start_dt - open_dt) > timedelta(hours=1):
            errors['clock_in_opens_at'] = "Clock-in cannot open more than 1 hour before class starts."
        
        # Check if clock-in closes too late (more than 1 hour after start)
        if (close_dt - start_dt) > timedelta(hours=1):
            errors['clock_in_closes_at'] = "Clock-in cannot close more than 1 hour after class starts."

        # Recurrence validation
        if self.recurring:
            if not self.recurrence_end_date:
                errors['recurrence_end_date'] = "End date is required for recurring schedules."
            if self.recurrence_pattern == 'weekly':
                if not isinstance(self.days_of_week, list) or len(self.days_of_week) == 0:
                    errors['days_of_week'] = "Please select at least one day of the week."
                else:
                    invalid = [d for d in self.days_of_week if not isinstance(d, int) or d < 0 or d > 6]
                    if invalid:
                        errors['days_of_week'] = "Days of week must be integers between 0 and 6."

        if errors:
            raise ValidationError(errors)
