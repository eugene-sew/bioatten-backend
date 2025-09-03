from django.db import models
from django.contrib.auth import get_user_model
from common.models import BaseModel
from django.utils import timezone
from students.models import StudentGroup

User = get_user_model()


class Faculty(BaseModel):
    """Model representing a faculty member with additional information."""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='faculty_profile',
        limit_choices_to={'role': User.FACULTY}
    )
    faculty_id = models.CharField(max_length=20, unique=True, db_index=True)
    department = models.CharField(max_length=100)
    # Many-to-many relationship to the courses (student groups) a faculty can teach/owns
    groups = models.ManyToManyField(
        StudentGroup,
        related_name='faculties',
        blank=True,
        help_text='Courses (student groups) assigned to this faculty'
    )
    designation = models.CharField(
        max_length=50,
        choices=[
            ('PROFESSOR', 'Professor'),
            ('ASSOCIATE_PROFESSOR', 'Associate Professor'),
            ('ASSISTANT_PROFESSOR', 'Assistant Professor'),
            ('LECTURER', 'Lecturer'),
            ('TEACHING_ASSISTANT', 'Teaching Assistant'),
        ]
    )
    office_location = models.CharField(max_length=50, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    join_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=[
            ('ACTIVE', 'Active'),
            ('INACTIVE', 'Inactive'),
            ('ON_LEAVE', 'On Leave'),
            ('RETIRED', 'Retired'),
        ],
        default='ACTIVE',
        db_index=True
    )
    
    class Meta:
        db_table = 'faculty'
        verbose_name = 'Faculty'
        verbose_name_plural = 'Faculty'
        ordering = ['user__last_name', 'user__first_name']
    
    def __str__(self):
        return f"{self.faculty_id} - {self.user.full_name} ({self.get_designation_display()})"

    def save(self, *args, **kwargs):
        # Auto-generate faculty_id if missing
        if not self.faculty_id:
            year_two = str(timezone.now().year)[-2:]
            prefix = f"FC0{year_two}00"
            last = (
                Faculty.objects.filter(faculty_id__startswith=prefix)
                .order_by('-faculty_id')
                .first()
            )
            if last and len(last.faculty_id) >= 10:
                try:
                    current = int(last.faculty_id[-3:])
                except ValueError:
                    current = 0
            else:
                current = 0
            next_inc = current + 1
            self.faculty_id = f"{prefix}{next_inc:03d}"
        super().save(*args, **kwargs)
