from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone
from attendance.models import AttendanceLog
from students.models import StudentGroup


@admin.register(AttendanceLog)
class AttendanceLogAdmin(admin.ModelAdmin):
    list_display = ['student', 'schedule', 'date', 'status', 'check_in_time', 'is_late']
    list_filter = ['status', 'date', 'schedule__assigned_group', 'is_manual_override']
    search_fields = ['student__student_id', 'student__user__first_name', 'student__user__last_name']
    date_hierarchy = 'date'
    ordering = ['-date', '-check_in_time']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'student__user', 'schedule__assigned_group'
        )


class ReportAdminSite(admin.AdminSite):
    site_header = "BioAttend Reports"
    site_title = "BioAttend Reports"
    index_title = "Reports Dashboard"

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        # Add quick links to reports
        today = timezone.now().date()
        week_ago = today - timezone.timedelta(days=7)
        month_ago = today - timezone.timedelta(days=30)
        
        # Get all active groups
        groups = StudentGroup.objects.all().order_by('name')
        
        report_links = []
        for group in groups:
            report_links.append({
                'name': f"{group.name} - Weekly Report",
                'url': f"/api/reports/attendance/?group={group.code}&from={week_ago}&to={today}",
                'description': "Last 7 days attendance report"
            })
            report_links.append({
                'name': f"{group.name} - Monthly Report",
                'url': f"/api/reports/attendance/?group={group.code}&from={month_ago}&to={today}",
                'description': "Last 30 days attendance report"
            })
        
        extra_context['report_links'] = report_links
        
        return super().index(request, extra_context)


# Create custom admin site for reports
report_admin_site = ReportAdminSite(name='report_admin')
