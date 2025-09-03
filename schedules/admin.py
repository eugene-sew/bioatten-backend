from django.contrib import admin
from .models import Schedule


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    """Admin configuration for Schedule model."""
    
    list_display = [
        'title', 'course_code', 'date', 'start_time', 'end_time', 
        'assigned_group', 'faculty', 'room', 'is_deleted'
    ]
    list_filter = [
        'date', 'assigned_group', 'faculty', 'is_deleted', 
        'created_at', 'updated_at'
    ]
    search_fields = [
        'title', 'course_code', 'room', 'description',
        'assigned_group__name', 'faculty__user__first_name', 
        'faculty__user__last_name'
    ]
    date_hierarchy = 'date'
    ordering = ['-date', 'start_time']
    
    fieldsets = (
        ('Schedule Information', {
            'fields': ('title', 'course_code', 'description')
        }),
        ('Date and Time', {
            'fields': ('date', 'start_time', 'end_time')
        }),
        ('Clock-in Configuration', {
            'fields': ('clock_in_opens_at', 'clock_in_closes_at'),
            'description': 'Configure when students can clock in for this class'
        }),
        ('Assignment', {
            'fields': ('assigned_group', 'faculty', 'room')
        }),
        ('System Information', {
            'fields': ('is_deleted', 'deleted_at', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        })
    )
    
    readonly_fields = ['created_at', 'updated_at', 'deleted_at']
    
    def get_queryset(self, request):
        """Include soft-deleted records in admin."""
        return self.model.objects.all()
