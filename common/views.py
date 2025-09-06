from django.shortcuts import render
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from authentication.permissions import IsAdmin
from .models import UserActivity
from .serializers import UserActivitySerializer, ActivityStatsSerializer


class RecentActivitiesView(generics.ListAPIView):
    """API view to get recent user activities for admin dashboard."""
    
    serializer_class = UserActivitySerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get_queryset(self):
        """Get recent activities with optional filtering."""
        queryset = UserActivity.objects.select_related('user').all()
        
        # Filter by days (default: last 7 days)
        days = getattr(self.request, 'query_params', self.request.GET).get('days', 7)
        try:
            days = int(days)
            if days > 0:
                since = timezone.now() - timedelta(days=days)
                queryset = queryset.filter(created_at__gte=since)
        except (ValueError, TypeError):
            pass
        
        # Filter by action type
        action_type = getattr(self.request, 'query_params', self.request.GET).get('action_type')
        if action_type:
            queryset = queryset.filter(action_type=action_type)
        
        # Filter by user
        user_id = getattr(self.request, 'query_params', self.request.GET).get('user_id')
        if user_id:
            try:
                queryset = queryset.filter(user_id=int(user_id))
            except (ValueError, TypeError):
                pass
        
        # Limit results (default: 50)
        limit = getattr(self.request, 'query_params', self.request.GET).get('limit', 50)
        try:
            limit = int(limit)
            if limit > 0:
                queryset = queryset[:limit]
        except (ValueError, TypeError):
            queryset = queryset[:50]
        
        return queryset


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdmin])
def activity_stats(request):
    """Get activity statistics for admin dashboard."""
    
    now = timezone.now()
    today = now.date()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    # Basic counts
    total_today = UserActivity.objects.filter(created_at__date=today).count()
    total_week = UserActivity.objects.filter(created_at__gte=week_ago).count()
    total_month = UserActivity.objects.filter(created_at__gte=month_ago).count()
    
    # Most active users (last 7 days)
    most_active = UserActivity.objects.filter(
        created_at__gte=week_ago
    ).values(
        'user__first_name', 'user__last_name', 'user__email'
    ).annotate(
        activity_count=Count('id')
    ).order_by('-activity_count')[:5]
    
    most_active_users = [
        {
            'name': f"{user['user__first_name']} {user['user__last_name']}".strip() or user['user__email'],
            'email': user['user__email'],
            'count': user['activity_count']
        }
        for user in most_active
    ]
    
    # Activity by type (last 7 days)
    activity_by_type = dict(
        UserActivity.objects.filter(
            created_at__gte=week_ago
        ).values('action_type').annotate(
            count=Count('id')
        ).values_list('action_type', 'count')
    )
    
    # Recent specific activities
    recent_logins = UserActivity.objects.filter(
        action_type='login',
        created_at__gte=week_ago
    ).count()
    
    recent_attendance = UserActivity.objects.filter(
        action_type__in=['check_in', 'check_out'],
        created_at__gte=week_ago
    ).count()
    
    stats_data = {
        'total_activities_today': total_today,
        'total_activities_week': total_week,
        'total_activities_month': total_month,
        'most_active_users': most_active_users,
        'activity_by_type': activity_by_type,
        'recent_logins': recent_logins,
        'recent_attendance': recent_attendance,
    }
    
    serializer = ActivityStatsSerializer(stats_data)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def log_custom_activity(request):
    """Allow manual logging of custom activities."""
    
    action_type = request.data.get('action_type')
    description = request.data.get('description')
    
    if not action_type or not description:
        return Response(
            {'error': 'action_type and description are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate action_type
    valid_actions = [choice[0] for choice in UserActivity.ACTION_TYPES]
    if action_type not in valid_actions:
        return Response(
            {'error': f'Invalid action_type. Must be one of: {valid_actions}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        activity = UserActivity.objects.create(
            user=request.user,
            action_type=action_type,
            description=description,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            request_path=request.path,
            request_method=request.method,
            target_model=request.data.get('target_model'),
            target_id=request.data.get('target_id'),
            extra_data=request.data.get('extra_data', {})
        )
        
        serializer = UserActivitySerializer(activity)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def get_client_ip(request):
    """Helper function to get client IP address."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
