from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from students.models import Student, StudentGroup

User = get_user_model()


class Command(BaseCommand):
    help = 'Create missing Student records for users with STUDENT role'

    def handle(self, *args, **options):
        # Find users with STUDENT role but no student_profile
        users_without_student = []
        for user in User.objects.filter(role=User.STUDENT):
            try:
                _ = user.student_profile
            except Student.DoesNotExist:
                users_without_student.append(user)

        if not users_without_student:
            self.stdout.write(
                self.style.SUCCESS('All STUDENT users already have Student records.')
            )
            return

        # Get or create a default student group
        default_group, created = StudentGroup.objects.get_or_create(
            name='Default Group',
            code='DEFAULT',
            defaults={
                'description': 'Default group for students without assigned groups',
                'academic_year': '2024-2025',
                'semester': 'Fall',
            }
        )

        if created:
            self.stdout.write(f'Created default StudentGroup: {default_group}')

        # Create Student records
        created_count = 0
        for user in users_without_student:
            student = Student.objects.create(
                user=user,
                group=default_group,
                enrollment_date=timezone.now().date(),
                status='ACTIVE',
            )
            self.stdout.write(f'Created Student record: {student.student_id} for user {user.username}')
            created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} Student records.')
        )
