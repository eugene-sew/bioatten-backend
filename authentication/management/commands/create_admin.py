from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from getpass import getpass

User = get_user_model()


class Command(BaseCommand):
    help = 'Create an admin user'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Admin email address',
        )
        parser.add_argument(
            '--first-name',
            type=str,
            help='First name',
        )
        parser.add_argument(
            '--last-name',
            type=str,
            help='Last name',
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Password (will prompt if not provided)',
        )
    
    def handle(self, *args, **options):
        email = options.get('email')
        if not email:
            email = input('Email: ')
        
        # Check if user already exists
        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.ERROR(f'User with email {email} already exists'))
            return
        
        first_name = options.get('first_name')
        if not first_name:
            first_name = input('First name: ')
        
        last_name = options.get('last_name')
        if not last_name:
            last_name = input('Last name: ')
        
        password = options.get('password')
        if not password:
            password = getpass('Password: ')
            password_confirm = getpass('Password (again): ')
            if password != password_confirm:
                self.stdout.write(self.style.ERROR('Passwords do not match'))
                return
        
        # Create the admin user
        user = User.objects.create_superuser(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        self.stdout.write(self.style.SUCCESS(f'Admin user "{email}" created successfully!'))
