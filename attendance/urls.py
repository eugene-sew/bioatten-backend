from django.urls import path
from .views import ClockInView, ClockOutView, ManualClockInRequestView, attendance_status
from .sse_views import attendance_updates_sse, test_attendance_broadcast
from .faculty_views import get_schedule_attendance, manual_clock_in

app_name = 'attendance'

urlpatterns = [
    path('api/attendance/clock_in/', ClockInView.as_view(), name='clock-in'),
    path('api/attendance/clock_out/', ClockOutView.as_view(), name='clock-out'),
    path('api/attendance/manual_clock_in_request/', ManualClockInRequestView.as_view(), name='manual-clock-in-request'),
    path('api/attendance/status/<int:schedule_id>/', attendance_status, name='attendance-status'),
    
    # Faculty endpoints
    path('api/attendance/schedule/<int:schedule_id>/', get_schedule_attendance, name='schedule-attendance'),
    path('api/attendance/schedule/<int:schedule_id>/manual-clock-in/', manual_clock_in, name='manual-clock-in'),
    
    # SSE endpoint for real-time updates
    path('api/attendance/updates/sse/<int:schedule_id>/', attendance_updates_sse, name='attendance-updates-sse'),
    path('api/attendance/test-broadcast/<int:schedule_id>/', test_attendance_broadcast, name='test-broadcast'),
]
