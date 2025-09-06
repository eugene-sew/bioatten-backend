from django.urls import path
from . import views, health_checks

urlpatterns = [
    path('activities/', views.RecentActivitiesView.as_view(), name='recent-activities'),
    path('activities/stats/', views.activity_stats, name='activity-stats'),
    path('activities/log/', views.log_custom_activity, name='log-activity'),
    path('health/', health_checks.system_health, name='system-health'),
    path('health/quick/', health_checks.quick_health, name='quick-health'),
]
