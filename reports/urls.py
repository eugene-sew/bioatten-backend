from django.urls import path
from .views import (
    AttendanceReportView,
    ChartDataView,
    StudentAttendanceReportView
)

app_name = 'reports'

urlpatterns = [
    # Main attendance report endpoint
    path('attendance/', AttendanceReportView.as_view(), name='attendance-report'),
    
    # Chart data endpoint
    path('charts/', ChartDataView.as_view(), name='chart-data'),
    
    # Individual student report
    path('student/<str:student_id>/', StudentAttendanceReportView.as_view(), name='student-report'),
]
