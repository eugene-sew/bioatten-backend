from rest_framework import viewsets, filters, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from datetime import datetime, date, timedelta, time
from .models import Schedule
from .permissions import IsAdminOrFacultyForWrite
from .serializers import ScheduleSerializer, ScheduleListSerializer
from students.models import StudentGroup
from faculty.models import Faculty


class SchedulePagination(PageNumberPagination):
    """Custom pagination for schedule endpoints."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ScheduleViewSet(viewsets.ModelViewSet):
    """ViewSet for managing Schedules with CRUD operations and filtering."""
    
    queryset = Schedule.objects.select_related('assigned_group', 'faculty__user')
    permission_classes = [IsAuthenticated, IsAdminOrFacultyForWrite]
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    search_fields = ['title', 'course_code', 'room', 'description']
    ordering_fields = ['date', 'start_time', 'created_at']
    ordering = ['date', 'start_time']
    pagination_class = SchedulePagination
    
    def get_serializer_class(self):
        """Use different serializers for list and detail views."""
        if self.action == 'list':
            return ScheduleListSerializer
        return ScheduleSerializer
    
    def get_queryset(self):
        """Apply filters based on query parameters."""
        queryset = super().get_queryset()
        
        # Exclude soft-deleted records
        queryset = queryset.filter(is_deleted=False)
        
        # Filter by user role - faculty can only see their own schedules
        user = self.request.user
        if user.is_authenticated and user.role == user.FACULTY:
            try:
                faculty = user.faculty_profile
                # Faculty can only see schedules assigned to them OR schedules for groups they're assigned to
                queryset = queryset.filter(
                    Q(faculty=faculty) | Q(assigned_group__in=faculty.groups.all())
                ).distinct()
            except Exception:
                # If faculty profile doesn't exist, return empty queryset
                return queryset.none()
        # Admin users can see all schedules (no additional filtering)
        
        # Date range filter
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from and date_to:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(date__range=[date_from, date_to])
            except ValueError:
                pass  # Invalid date format, ignore filter
        elif date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
                queryset = queryset.filter(date__gte=date_from)
            except ValueError:
                pass
        elif date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
                queryset = queryset.filter(date__lte=date_to)
            except ValueError:
                pass
        
        # Group filter
        group = self.request.query_params.get('group')
        if group:
            queryset = queryset.filter(assigned_group__id=group)
        
        # Faculty filter
        faculty = self.request.query_params.get('faculty')
        if faculty:
            queryset = queryset.filter(faculty__id=faculty)
        
        # Course code filter
        course_code = self.request.query_params.get('course_code')
        if course_code:
            queryset = queryset.filter(course_code__icontains=course_code)
        
        # Date filter (specific date)
        date_filter = self.request.query_params.get('date')
        if date_filter:
            try:
                date_filter = datetime.strptime(date_filter, '%Y-%m-%d').date()
                queryset = queryset.filter(date=date_filter)
            except ValueError:
                pass
        
        return queryset

    def _parse_frontend_times(self, data):
        """Accept frontend-style datetime-local/ISO inputs and derive date/time fields.

        Mutates and returns a copy of data with:
        - date: YYYY-MM-DD (if derivable)
        - start_time, end_time: HH:MM:SS
        - clock_in_opens_at/clock_in_closes_at defaults if missing (15m before/after start)
        - room mapped from location if provided
        """
        d = data.copy()

        def parse_dt(val):
            # Accept 'YYYY-MM-DDTHH:MM' or ISO string
            try:
                # Try full ISO first
                dt = datetime.fromisoformat(val.replace('Z', '+00:00'))
                return dt
            except Exception:
                return None

        # Normalize start_time and end_time
        start_val = d.get('start_time')
        end_val = d.get('end_time')
        parsed_start = parse_dt(start_val) if isinstance(start_val, str) else None
        parsed_end = parse_dt(end_val) if isinstance(end_val, str) else None

        # If no explicit date provided or blank, derive from parsed_start
        if (not d.get('date') or str(d.get('date')).strip() == '') and parsed_start:
            d['date'] = parsed_start.date().isoformat()

        # Replace time fields with HH:MM:SS if parsed
        def fmt_time(dt_obj):
            t = dt_obj.timetz() if hasattr(dt_obj, 'timetz') else dt_obj
            # Serialize as HH:MM:SS
            return t.replace(microsecond=0).strftime('%H:%M:%S')

        if parsed_start:
            d['start_time'] = fmt_time(parsed_start)
        if parsed_end:
            d['end_time'] = fmt_time(parsed_end)

        # Map location -> room (preserve location field)
        if d.get('location') and not d.get('room'):
            d['room'] = d.get('location')

        # Defaults for course_code
        if not d.get('course_code'):
            # Use a generic placeholder; can be edited later
            d['course_code'] = 'NA'

        # Compute default clock-in windows if missing and start_time present
        if d.get('start_time') and (not d.get('clock_in_opens_at') or not d.get('clock_in_closes_at')):
            try:
                # Build a dummy datetime to do arithmetic
                dt_dummy = datetime(2000, 1, 1)
                start_parts = [int(x) for x in str(d['start_time']).split(':')[:2]]
                start_t = time(hour=start_parts[0], minute=start_parts[1])
                start_dt = datetime.combine(dt_dummy.date(), start_t)
                opens_dt = start_dt - timedelta(minutes=15)
                closes_dt = start_dt + timedelta(minutes=15)
                if not d.get('clock_in_opens_at'):
                    d['clock_in_opens_at'] = opens_dt.time().strftime('%H:%M:%S')
                if not d.get('clock_in_closes_at'):
                    d['clock_in_closes_at'] = closes_dt.time().strftime('%H:%M:%S')
            except Exception:
                pass

        # Recurrence end date may come as ISO datetime; convert to YYYY-MM-DD
        rec_end = d.get('recurrence_end_date')
        if isinstance(rec_end, str) and rec_end:
            try:
                rec_dt = datetime.fromisoformat(rec_end.replace('Z', '+00:00'))
                d['recurrence_end_date'] = rec_dt.date().isoformat()
            except Exception:
                # If already in YYYY-MM-DD or invalid, leave as-is and let serializer validate
                pass

        # Keep recurrence and location fields now supported by model/serializer

        return d

    def _ensure_faculty_and_group(self, request, data):
        """Ensure faculty and assigned_group IDs are present.

        - faculty defaults to current user's faculty_profile
        - assigned_group defaults to or creates an 'Unassigned' group
        """
        d = data.copy()

        # Faculty
        if not d.get('faculty') and hasattr(request.user, 'faculty_profile'):
            d['faculty'] = request.user.faculty_profile.id

        # Assigned group
        if not d.get('assigned_group'):
            group, _ = StudentGroup.objects.get_or_create(
                name='Unassigned', code='UNASSIGNED', defaults={'academic_year': 'NA', 'semester': 'NA'}
            )
            d['assigned_group'] = group.id

        return d
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's schedules."""
        today = date.today()
        queryset = self.get_queryset().filter(date=today)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming schedules (next 7 days)."""
        today = date.today()
        queryset = self.get_queryset().filter(
            date__gte=today,
            date__lte=today + timedelta(days=7)
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_group(self, request):
        """Get schedules grouped by student group."""
        group_id = request.query_params.get('group_id')
        if not group_id:
            return Response(
                {"detail": "group_id parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(assigned_group__id=group_id)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_faculty(self, request):
        """Get schedules for a specific faculty member."""
        faculty_id = request.query_params.get('faculty_id')
        if not faculty_id:
            return Response(
                {"detail": "faculty_id parameter is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(faculty__id=faculty_id)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete the schedule instead of hard delete."""
        instance = self.get_object()
        instance.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def create(self, request, *args, **kwargs):
        """Create schedule accepting frontend-style payloads.

        Accepts start_time/end_time as ISO datetimes, optional location, and missing
        course_code/clock-in windows. Fills sensible defaults and maps fields to
        the Schedule model requirements.
        """
        cleaned = self._parse_frontend_times(request.data)
        cleaned = self._ensure_faculty_and_group(request, cleaned)

        serializer = self.get_serializer(data=cleaned)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        """Update schedule accepting frontend-style payloads (ISO datetimes, location mapping)."""
        partial = kwargs.pop('partial', False)
        cleaned = self._parse_frontend_times(request.data)
        cleaned = self._ensure_faculty_and_group(request, cleaned)

        instance = self.get_object()
        serializer = self.get_serializer(instance, data=cleaned, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        """PATCH handler that routes to update() with partial flag."""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @action(detail=False, methods=['post'])
    def conflicts(self, request):
        """Check for schedule conflicts.

        Request body may contain:
        - date (YYYY-MM-DD) or derivable from start_time ISO
        - start_time/end_time (ISO or HH:MM)
        - location (optional, maps to room)
        - exclude_id (optional) to ignore a specific schedule
        - days_of_week/recurring are accepted but ignored in this basic check

        Returns a list of conflict messages.
        """
        data = self._parse_frontend_times(request.data)

        date_str = data.get('date')
        start_t = data.get('start_time')
        end_t = data.get('end_time')
        room = data.get('room')
        exclude_id = data.get('exclude_id')

        if not (date_str and start_t and end_t):
            return Response({'detail': 'date, start_time, and end_time are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            start_parts = [int(x) for x in str(start_t).split(':')[:2]]
            end_parts = [int(x) for x in str(end_t).split(':')[:2]]
            start_time_obj = time(hour=start_parts[0], minute=start_parts[1])
            end_time_obj = time(hour=end_parts[0], minute=end_parts[1])
        except Exception:
            return Response({'detail': 'Invalid date/time format'}, status=status.HTTP_400_BAD_REQUEST)

        qs = self.get_queryset().filter(date=date(target_date.year, target_date.month, target_date.day))
        if exclude_id:
            qs = qs.exclude(id=exclude_id)

        conflicts = []
        for sched in qs:
            # Check time overlap
            overlap = (start_time_obj < sched.end_time) and (end_time_obj > sched.start_time)
            if not overlap:
                continue

            # Build reasons: same faculty or same room
            reasons = []
            if hasattr(self.request.user, 'faculty_profile') and sched.faculty_id == self.request.user.faculty_profile.id:
                reasons.append('same faculty')
            if room and sched.room and sched.room == room:
                reasons.append('same room')
            if not reasons:
                reasons.append('time overlap')

            conflicts.append({
                'id': sched.id,
                'message': f"Conflicts with '{sched.title}' on {sched.date} {sched.start_time}-{sched.end_time} ({', '.join(reasons)})"
            })

        return Response(conflicts)
