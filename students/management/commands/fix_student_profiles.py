from django.core.management.base import BaseCommand
from django.utils import timezone
from authentication.models import User
from students.models import Student, StudentGroup


class Command(BaseCommand):
    help = 'Create Student profiles for users with STUDENT role who are missing profiles'

    def handle(self, *args, **options):
        # Get all users with STUDENT role who don't have a student profile
        student_users_without_profile = []
        
        for user in User.objects.filter(role=User.STUDENT):
            try:
                user.student_profile
            except Student.DoesNotExist:
                student_users_without_profile.append(user)
        
        if not student_users_without_profile:
            self.stdout.write(
                self.style.SUCCESS('All student users already have profiles.')
            )
            return
        
        # Get or create a default group
        default_group, created = StudentGroup.objects.get_or_create(
            code='DEFAULT',
            defaults={
                'name': 'Default Group',
                'academic_year': '2024-2025',
                'semester': 'Fall',
                'description': 'Default group for students without assigned groups'
            }
        )
        
        if created:
            self.stdout.write(f'Created default group: {default_group.name}')
        
        # Create student profiles
        created_count = 0
        for user in student_users_without_profile:
            student = Student.objects.create(
                user=user,
                group=default_group,
                enrollment_date=timezone.now().date(),
                status='ACTIVE'
            )
            self.stdout.write(f'Created profile for {user.email}: {student.student_id}')
            created_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} student profiles.')
        )
