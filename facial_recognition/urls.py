from django.urls import path
from .views import (
    StudentEnrollmentView,
    EnrollmentAttemptsView,
    enrollment_statistics,
    SelfEnrollmentView,
    SelfEnrollmentStatusView,
)

app_name = 'facial_recognition'

urlpatterns = [
    # Self-enrollment endpoints (must come before generic student endpoints)
    path('students/me/enroll/', SelfEnrollmentView.as_view(), name='student_enroll_me'),
    path('students/me/enrollment/', SelfEnrollmentStatusView.as_view(), name='student_enrollment_me'),
    
    # Generic student enrollment endpoints
    path('students/<str:student_id>/enroll/', StudentEnrollmentView.as_view(), name='student_enroll'),
    path('students/<str:student_id>/enrollment/', StudentEnrollmentView.as_view(), name='student_enrollment'),
    path('students/<str:student_id>/enrollment-attempts/', EnrollmentAttemptsView.as_view(), name='enrollment_attempts'),
    
    # Statistics endpoint
    path('enrollment-statistics/', enrollment_statistics, name='enrollment_statistics'),
]
