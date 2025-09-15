from django.urls import path
from . import views
from .verification_views import (
    FacialVerificationView,
    BulkFacialVerificationView,
    facial_recognition_status
)

app_name = 'facial_recognition'

urlpatterns = [
    # Student enrollment endpoints
    path('students/<str:student_id>/enroll/', views.StudentEnrollmentView.as_view(), name='student-enroll'),
    path('students/<str:student_id>/enrollment/', views.StudentEnrollmentView.as_view(), name='student-enrollment-status'),
    
    # Enrollment attempts
    path('students/<str:student_id>/attempts/', views.EnrollmentAttemptsView.as_view(), name='enrollment-attempts'),
    
    # Self enrollment endpoints
    path('self/enroll/', views.SelfEnrollmentView.as_view(), name='self-enroll'),
    path('self/status/', views.SelfEnrollmentStatusView.as_view(), name='self-enrollment-status'),
    
    # Statistics endpoint
    path('enrollment-statistics/', views.EnrollmentStatisticsView.as_view(), name='enrollment-statistics'),
    
    # Facial verification endpoints
    path('verify/', FacialVerificationView.as_view(), name='facial-verification'),
    path('identify/', BulkFacialVerificationView.as_view(), name='bulk-facial-verification'),
    path('status/', facial_recognition_status, name='facial-recognition-status'),
]
