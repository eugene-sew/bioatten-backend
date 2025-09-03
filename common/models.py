from django.db import models
from django.utils import timezone


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
