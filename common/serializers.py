from rest_framework import serializers
from .models import UserActivity


class UserActivitySerializer(serializers.ModelSerializer):
    """Serializer for UserActivity model."""
    
    user_name = serializers.SerializerMethodField()
    user_role = serializers.SerializerMethodField()
    action_display = serializers.CharField(source='get_action_type_display', read_only=True)
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = UserActivity
        fields = [
            'id', 'user_name', 'user_role', 'action_type', 'action_display',
            'description', 'created_at', 'time_ago', 'ip_address',
            'request_path', 'request_method', 'target_model', 'target_id'
        ]
        read_only_fields = ['created_at']
    
    def get_user_name(self, obj):
        """Get the full name of the user."""
        return obj.user.full_name or obj.user.email
    
    def get_user_role(self, obj):
        """Get the role of the user."""
        return obj.user.role if hasattr(obj.user, 'role') else 'USER'
    
    def get_time_ago(self, obj):
        """Get a human-readable time difference."""
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff < timedelta(minutes=1):
            return "Just now"
        elif diff < timedelta(hours=1):
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff < timedelta(days=7):
            days = diff.days
            return f"{days} day{'s' if days != 1 else ''} ago"
        else:
            return obj.created_at.strftime("%b %d, %Y")


class ActivityStatsSerializer(serializers.Serializer):
    """Serializer for activity statistics."""
    
    total_activities_today = serializers.IntegerField()
    total_activities_week = serializers.IntegerField()
    total_activities_month = serializers.IntegerField()
    most_active_users = serializers.ListField()
    activity_by_type = serializers.DictField()
    recent_logins = serializers.IntegerField()
    recent_attendance = serializers.IntegerField()
