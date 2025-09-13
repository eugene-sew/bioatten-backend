from django.urls import path
from .views import (
    AttendanceReportView,
    ChartDataView,
    StudentAttendanceReportView,
    DetailedAttendanceRecordsView,
    DashboardStatsView
)

app_name = 'reports'

urlpatterns = [
    # Main attendance report endpoint
    path('attendance/', AttendanceReportView.as_view(), name='attendance-report'),
    
    # Detailed attendance records with student names
    path('attendance/records/', DetailedAttendanceRecordsView.as_view(), name='detailed-records'),
    
    # Chart data endpoint
    path('charts/', ChartDataView.as_view(), name='chart-data'),
    
    # Dashboard statistics endpoint
    path('dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    
    # Individual student report
    path('student/<str:student_id>/', StudentAttendanceReportView.as_view(), name='student-report'),
]
