from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Faculty
from .serializers import FacultySerializer
from students.serializers import StudentGroupMiniSerializer


class FacultyViewSet(viewsets.ModelViewSet):
    queryset = Faculty.objects.select_related('user').prefetch_related('groups')
    serializer_class = FacultySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        user_id = self.request.query_params.get('user')
        if user_id:
            qs = qs.filter(user_id=user_id)
        return qs

    # Enforce admin-only for write operations
    def _ensure_admin(self, request):
        user = getattr(request, 'user', None)
        if not user or getattr(user, 'role', None) != 'ADMIN':
            return Response({'detail': 'Admin privileges required.'}, status=status.HTTP_403_FORBIDDEN)
        return None

    def create(self, request, *args, **kwargs):
        resp = self._ensure_admin(request)
        if resp:
            return resp
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        resp = self._ensure_admin(request)
        if resp:
            return resp
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        resp = self._ensure_admin(request)
        if resp:
            return resp
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        resp = self._ensure_admin(request)
        if resp:
            return resp
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='my-groups')
    def my_groups(self, request):
        """Return groups (courses) assigned to the current faculty user."""
        # Only FACULTY role is allowed to access this endpoint
        if getattr(request.user, 'role', None) != 'FACULTY':
            return Response({'detail': 'Only faculty users have assigned courses.'}, status=status.HTTP_403_FORBIDDEN)

        # If the user is FACULTY but has no Faculty profile yet, return an empty list instead of 403
        faculty = getattr(request.user, 'faculty_profile', None)
        if not faculty:
            return Response([])

        groups = faculty.groups.all().order_by('name')
        data = StudentGroupMiniSerializer(groups, many=True).data
        return Response(data)
