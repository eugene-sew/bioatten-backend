from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.utils import timezone
from datetime import timedelta
import secrets

from students.models import Student, StudentGroup
from faculty.models import Faculty
from common.services import send_account_creation_email

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model with optional embedded profiles."""

    student_profile = serializers.SerializerMethodField(read_only=True)
    faculty_profile = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'role', 'is_active', 'date_joined',
            'student_profile', 'faculty_profile'
        ]
        read_only_fields = ['id', 'date_joined', 'student_profile', 'faculty_profile']

    def get_student_profile(self, obj):
        # Include minimal student info for consumers that need group filtering
        try:
            student = obj.student_profile  # OneToOne related_name
        except Exception:
            return None
        if not student:
            return None
        group = student.group if getattr(student, 'group', None) else None
        return {
            'student_id': getattr(student, 'student_id', None),
            'group': (
                {
                    'id': getattr(group, 'id', None),
                    'name': getattr(group, 'name', None),
                    'code': getattr(group, 'code', None),
                }
                if group else None
            ),
            'status': getattr(student, 'status', None),
        }

    def get_faculty_profile(self, obj):
        try:
            faculty = obj.faculty_profile  # OneToOne related_name
        except Exception:
            return None
        if not faculty:
            return None
        return {
            'id': getattr(faculty, 'id', None),
            'faculty_id': getattr(faculty, 'faculty_id', None),
            'department': getattr(faculty, 'department', None),
        }


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration (admin-only) with optional profile creation."""

    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    # Optional profile fields
    student_id = serializers.CharField(write_only=True, required=False, allow_blank=True)
    group = serializers.PrimaryKeyRelatedField(
        queryset=StudentGroup.objects.all(), write_only=True, required=False, allow_null=True
    )
    faculty_id = serializers.CharField(write_only=True, required=False, allow_blank=True)
    department = serializers.CharField(write_only=True, required=False, allow_blank=True)
    # Optional initial group assignments for faculty users
    groups = serializers.PrimaryKeyRelatedField(
        queryset=StudentGroup.objects.all(), many=True, write_only=True, required=False
    )

    class Meta:
        model = User
        fields = [
            'email', 'password', 'password_confirm', 'first_name', 'last_name', 'role',
            'student_id', 'group', 'faculty_id', 'department', 'groups'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})

        role = attrs.get('role')
        if role == User.STUDENT:
            # For students, only require group; student_id will auto-generate if omitted
            if not attrs.get('group'):
                raise serializers.ValidationError({"group": "This field is required for students."})
        elif role == User.FACULTY:
            # faculty_id will auto-generate if omitted
            pass
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data.pop('password_confirm', None)

        # Extract optional profile fields
        student_id = validated_data.pop('student_id', None)
        group = validated_data.pop('group', None)
        faculty_id = validated_data.pop('faculty_id', None)
        department = validated_data.pop('department', '')
        groups = validated_data.pop('groups', [])

        user = User.objects.create_user(password=password, **validated_data)

        # Create linked profile based on role
        role = user.role
        if role == User.STUDENT:
            Student.objects.create(
                user=user,
                student_id=student_id,
                group=group,
                enrollment_date=timezone.now().date(),
                status='ACTIVE',
            )
        elif role == User.FACULTY:
            # Ensure required Faculty fields are set. The Faculty model requires
            # join_date and designation; department should not be None for CharField.
            faculty = Faculty.objects.create(
                user=user,
                faculty_id=faculty_id,
                department=department or '',
                designation='LECTURER',
                join_date=timezone.now().date(),
                status='ACTIVE',
            )
            # Assign initial groups if provided
            if groups:
                faculty.groups.set(groups)

        # Send account creation email
        send_account_creation_email(user, password)

        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom token serializer to include user data in response."""
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add user information to the response
        data['user'] = {
            'id': str(self.user.id),
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'role': self.user.role,
            'full_name': self.user.full_name
        }
        
        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for requesting password reset."""
    
    email = serializers.EmailField()
    
    def validate_email(self, value):
        try:
            User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("No user found with this email address.")
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for confirming password reset."""
    
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        # Validate token
        try:
            user = User.objects.get(reset_token=attrs['token'])
            # Check if token is expired (24 hours)
            if user.reset_token_created < timezone.now() - timedelta(hours=24):
                raise serializers.ValidationError({"token": "Reset token has expired."})
        except User.DoesNotExist:
            raise serializers.ValidationError({"token": "Invalid reset token."})
        
        attrs['user'] = user
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password (authenticated users)."""
    
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs
