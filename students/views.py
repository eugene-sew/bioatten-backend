from rest_framework import permissions, viewsets, mixins, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from django.db.models import Q
from django.shortcuts import get_object_or_404

from authentication.models import User
from faculty.models import Faculty
from .models import Student, StudentGroup
from .serializers import StudentListSerializer, StudentGroupMiniSerializer
from authentication.permissions import IsAdmin
from schedules.models import Schedule


class IsFaculty(permissions.BasePermission):
    """Allow access only to authenticated faculty users."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == User.FACULTY)


class FacultyStudentViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    Read-only endpoint returning students associated with the current faculty.

    Association rule (current schema): a student belongs to a StudentGroup. A faculty
    is linked to groups via schedules (Schedule.assigned_group with Schedule.faculty == current faculty).
    We derive groups from schedules and list distinct students in those groups.
    """

    serializer_class = StudentListSerializer
    permission_classes = [permissions.IsAuthenticated, IsFaculty]

    def get_queryset(self):
        user = self.request.user
        faculty = Faculty.objects.filter(user=user).first()
        if not faculty:
            return Student.objects.none()

        # Use direct faculty.groups relationship instead of schedule-based filtering
        # This ensures students appear immediately when assigned to faculty groups
        qs = (
            Student.objects.select_related("user", "group")
            .filter(group__in=faculty.groups.all())
            .distinct()
        )

        # Optional search by name, id, email, group name
        q = self.request.query_params.get("search")
        if q:
            qs = qs.filter(
                Q(student_id__icontains=q)
                | Q(user__first_name__icontains=q)
                | Q(user__last_name__icontains=q)
                | Q(user__email__icontains=q)
                | Q(group__name__icontains=q)
            )

        # Optional filter by group id
        group_id = self.request.query_params.get("group")
        if group_id:
            qs = qs.filter(group_id=group_id)

        return qs.order_by("user__last_name", "user__first_name")


class StudentGroupViewSet(viewsets.ModelViewSet):
    """
    Admin: full CRUD on student groups.
    Faculty/Student: read-only and only see assigned groups.
    """

    serializer_class = StudentGroupMiniSerializer
    pagination_class = None

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        # Non-safe methods require admin
        return [permissions.IsAuthenticated(), IsAdmin()]

    def get_queryset(self):
        user = self.request.user
        qs = StudentGroup.objects.all().order_by("name")
        if not user.is_authenticated:
            return StudentGroup.objects.none()
        if user.is_admin():
            return qs
        if user.is_faculty():
            # Groups with schedules assigned to this faculty
            return StudentGroup.objects.filter(
                schedules__faculty__user=user
            ).distinct().order_by("name")
        if user.is_student():
            try:
                sg = user.student_profile.group
                return StudentGroup.objects.filter(id=sg.id)
            except Exception:
                return StudentGroup.objects.none()
        return StudentGroup.objects.none()


class StudentProfileUpdateView(APIView):
    """
    API endpoint to update student profile information, including course assignment.
    Only accessible by admin users.
    """
    permission_classes = [permissions.IsAuthenticated, IsAdmin]
    
    def patch(self, request, student_id):
        """Update student profile."""
        try:
            student = get_object_or_404(Student, student_id=student_id)
            
            # Get the new group ID from request data
            group_id = request.data.get('group')
            if group_id:
                try:
                    new_group = StudentGroup.objects.get(id=group_id)
                    student.group = new_group
                    student.save()
                    
                    return Response({
                        'success': True,
                        'message': f'Student {student.user.full_name} successfully assigned to course {new_group.name}',
                        'student': {
                            'id': student.student_id,
                            'name': student.user.full_name,
                            'group': {
                                'id': new_group.id,
                                'name': new_group.name,
                                'code': new_group.code
                            }
                        }
                    })
                except StudentGroup.DoesNotExist:
                    return Response({
                        'success': False,
                        'error': 'Invalid course selected'
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({
                    'success': False,
                    'error': 'Course assignment is required'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Student.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Student not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Failed to update student profile: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
