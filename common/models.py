from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


class TimestampedModel(models.Model):
    """Abstract base model with automatic timestamp fields."""
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True


class SoftDeletableModel(models.Model):
    """Abstract base model with soft delete functionality."""
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        """Mark the object as deleted without actually deleting it."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def restore(self):
        """Restore a soft-deleted object."""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=['is_deleted', 'deleted_at'])


class BaseModel(TimestampedModel, SoftDeletableModel):
    """Base model combining timestamps and soft delete functionality."""
    
    class Meta:
        abstract = True


class UserActivity(TimestampedModel):
    """Model to track user activities across the system."""
    
    ACTION_TYPES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('check_in', 'Check In'),
        ('check_out', 'Check Out'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('view', 'View'),
        ('enroll', 'Biometric Enrollment'),
        ('schedule_create', 'Schedule Created'),
        ('attendance_mark', 'Attendance Marked'),
        ('user_create', 'User Created'),
        ('group_create', 'Group Created'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    request_path = models.CharField(max_length=500, null=True, blank=True)
    request_method = models.CharField(max_length=10, null=True, blank=True)
    
    # Optional metadata for specific actions
    target_model = models.CharField(max_length=100, null=True, blank=True)  # Model name
    target_id = models.CharField(max_length=100, null=True, blank=True)     # Object ID
    extra_data = models.JSONField(default=dict, blank=True)                 # Additional context
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['action_type', '-created_at']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.full_name} - {self.get_action_type_display()} at {self.created_at}"
