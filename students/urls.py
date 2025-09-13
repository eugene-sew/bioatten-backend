from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import FacultyStudentViewSet, StudentGroupViewSet, StudentProfileUpdateView

router = DefaultRouter()
router.register(r'faculty/students', FacultyStudentViewSet, basename='faculty-students')
router.register(r'students/groups', StudentGroupViewSet, basename='student-groups')

urlpatterns = router.urls + [
    path('students/<str:student_id>/profile/', StudentProfileUpdateView.as_view(), name='student-profile-update'),
]
