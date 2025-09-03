from django.db import models
from django.contrib.auth import get_user_model
from common.models import BaseModel
from django.utils import timezone

User = get_user_model()


class StudentGroup(BaseModel):
    """Model representing a student group/class."""
    
    name = models.CharField(max_length=100, unique=True, db_index=True)
    code = models.CharField(max_length=20, unique=True, db_index=True)
    description = models.TextField(blank=True)
    academic_year = models.CharField(max_length=9)  # e.g., "2023-2024"
    semester = models.CharField(max_length=20)  # e.g., "Fall", "Spring"
    
    class Meta:
        db_table = 'student_groups'
        verbose_name = 'Student Group'
        verbose_name_plural = 'Student Groups'
        ordering = ['-academic_year', 'semester', 'name']
        unique_together = [['name', 'academic_year', 'semester']]
    
    def __str__(self):
        return f"{self.name} ({self.code}) - {self.academic_year} {self.semester}"


class Student(BaseModel):
    """Model representing a student with additional information."""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile',
        limit_choices_to={'role': User.STUDENT}
    )
    student_id = models.CharField(max_length=20, unique=True, db_index=True)
    group = models.ForeignKey(
        StudentGroup,
        on_delete=models.PROTECT,
        related_name='students'
    )
    enrollment_date = models.DateField()
    graduation_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('ACTIVE', 'Active'),
            ('INACTIVE', 'Inactive'),
            ('GRADUATED', 'Graduated'),
            ('SUSPENDED', 'Suspended'),
            ('WITHDRAWN', 'Withdrawn'),
        ],
        default='ACTIVE',
        db_index=True
    )
    
    class Meta:
        db_table = 'students'
        verbose_name = 'Student'
        verbose_name_plural = 'Students'
        ordering = ['user__last_name', 'user__first_name']
    
    def __str__(self):
        return f"{self.student_id} - {self.user.full_name}"

    def save(self, *args, **kwargs):
        # Auto-generate student_id if missing
        if not self.student_id:
            year_two = str(timezone.now().year)[-2:]
            prefix = f"ST0{year_two}00"
            # Find the current max increment for this year
            last = (
                Student.objects.filter(student_id__startswith=prefix)
                .order_by('-student_id')
                .first()
            )
            if last and len(last.student_id) >= 10:
                try:
                    current = int(last.student_id[-3:])
                except ValueError:
                    current = 0
            else:
                current = 0
            next_inc = current + 1
            self.student_id = f"{prefix}{next_inc:03d}"
        super().save(*args, **kwargs)
