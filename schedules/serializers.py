from rest_framework import serializers
from datetime import datetime, timedelta
from .models import Schedule
from students.models import StudentGroup
from faculty.models import Faculty


class ScheduleSerializer(serializers.ModelSerializer):
    """Serializer for the Schedule model with comprehensive validation."""
    
    # Nested serializers for read operations
    assigned_group_detail = serializers.SerializerMethodField(read_only=True)
    faculty_detail = serializers.SerializerMethodField(read_only=True)
    # Explicit optional write fields
    faculty = serializers.PrimaryKeyRelatedField(
        queryset=Faculty.objects.all(), required=False, allow_null=True, write_only=True
    )
    assigned_group = serializers.PrimaryKeyRelatedField(
        queryset=StudentGroup.objects.all(), required=False, allow_null=True, write_only=True
    )
    
    class Meta:
        model = Schedule
        fields = [
            'id', 'title', 'course_code', 'date', 'start_time', 'end_time',
            'clock_in_opens_at', 'clock_in_closes_at', 'assigned_group',
            'assigned_group_detail', 'faculty', 'faculty_detail', 'room', 'location',
            'description', 'is_active', 'recurring', 'recurrence_pattern',
            'recurrence_end_date', 'days_of_week', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        # Disable automatic UniqueTogetherValidator so we can allow missing faculty
        validators = []
        extra_kwargs = {
            'course_code': {'required': False, 'allow_blank': True},
        }
    
    def get_assigned_group_detail(self, obj):
        """Return detailed information about the assigned group."""
        if obj.assigned_group:
            return {
                'id': obj.assigned_group.id,
                'name': obj.assigned_group.name,
                'code': obj.assigned_group.code,
            }
        return None
    
    def get_faculty_detail(self, obj):
        """Return detailed information about the faculty."""
        if obj.faculty:
            return {
                'id': obj.faculty.id,
                'faculty_id': obj.faculty.faculty_id,
                'name': obj.faculty.user.full_name,
                'department': obj.faculty.department,
            }
        return None
    
    def validate(self, data):
        """Ensure logical time windows and other custom validation rules."""
        errors = {}
        
        # Get the fields, handling both create and update scenarios
        start_time = data.get('start_time', self.instance.start_time if self.instance else None)
        end_time = data.get('end_time', self.instance.end_time if self.instance else None)
        clock_in_opens_at = data.get('clock_in_opens_at', self.instance.clock_in_opens_at if self.instance else None)
        clock_in_closes_at = data.get('clock_in_closes_at', self.instance.clock_in_closes_at if self.instance else None)
        
        if not all([start_time, end_time, clock_in_opens_at, clock_in_closes_at]):
            raise serializers.ValidationError("All time fields are required.")
        
        # Validate time order
        if start_time >= end_time:
            errors['end_time'] = "End time must be after start time."
        
        # Validate clock-in window
        if clock_in_opens_at > start_time:
            errors['clock_in_opens_at'] = "Clock-in cannot open after the class starts."
        
        if clock_in_closes_at < start_time:
            errors['clock_in_closes_at'] = "Clock-in cannot close before the class starts."
        
        if clock_in_opens_at >= clock_in_closes_at:
            errors['clock_in_closes_at'] = "Clock-in close time must be after open time."
        
        # Validate clock-in window is within reasonable bounds
        # Convert times to datetime for calculation
        dummy_date = datetime(2000, 1, 1)
        start_dt = datetime.combine(dummy_date, start_time)
        open_dt = datetime.combine(dummy_date, clock_in_opens_at)
        close_dt = datetime.combine(dummy_date, clock_in_closes_at)
        
        # Check if clock-in opens too early (more than 1 hour before start)
        if (start_dt - open_dt) > timedelta(hours=1):
            errors['clock_in_opens_at'] = "Clock-in cannot open more than 1 hour before class starts."
        
        # Check if clock-in closes too late (more than 1 hour after start)
        if (close_dt - start_dt) > timedelta(hours=1):
            errors['clock_in_closes_at'] = "Clock-in cannot close more than 1 hour after class starts."
        
        if errors:
            raise serializers.ValidationError(errors)
        
        # Recurrence validation paralleling model.clean for serializer-level checks
        recurring = data.get('recurring', self.instance.recurring if self.instance else False)
        recurrence_pattern = data.get('recurrence_pattern', self.instance.recurrence_pattern if self.instance else 'weekly')
        recurrence_end_date = data.get('recurrence_end_date', self.instance.recurrence_end_date if self.instance else None)
        days = data.get('days_of_week', self.instance.days_of_week if self.instance else [])

        if recurring:
            if not recurrence_end_date:
                errors['recurrence_end_date'] = "End date is required for recurring schedules."
            if recurrence_pattern == 'weekly':
                if not isinstance(days, list) or len(days) == 0:
                    errors['days_of_week'] = "Please select at least one day of the week."
                else:
                    invalid = [d for d in days if not isinstance(d, int) or d < 0 or d > 6]
                    if invalid:
                        errors['days_of_week'] = "Days of week must be integers between 0 and 6."

        if errors:
            raise serializers.ValidationError(errors)

        # Conditional uniqueness checks (replace UniqueTogetherValidator)
        # Resolve final values using instance defaults when updating
        assigned_group = data.get('assigned_group', getattr(self.instance, 'assigned_group', None) if self.instance else None)
        date_val = data.get('date', getattr(self.instance, 'date', None) if self.instance else None)
        start_val = data.get('start_time', getattr(self.instance, 'start_time', None) if self.instance else None)
        faculty_val = data.get('faculty', getattr(self.instance, 'faculty', None) if self.instance else None)

        if assigned_group and date_val and start_val:
            qs = Schedule.objects.filter(assigned_group=assigned_group, date=date_val, start_time=start_val)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                errors['start_time'] = 'This group already has a schedule at the same start time on this date.'

        if faculty_val is not None and date_val and start_val:
            qs2 = Schedule.objects.filter(faculty=faculty_val, date=date_val, start_time=start_val)
            if self.instance:
                qs2 = qs2.exclude(pk=self.instance.pk)
            if qs2.exists():
                errors['start_time'] = 'This faculty already has a schedule at the same start time on this date.'

        if errors:
            raise serializers.ValidationError(errors)

        return data
    
    def create(self, validated_data):
        """Create a new schedule with model validation."""
        # Map location to room if room missing for compatibility
        if validated_data.get('location') and not validated_data.get('room'):
            validated_data['room'] = validated_data.get('location')
        # Default faculty from request context if absent
        request = self.context.get('request') if hasattr(self, 'context') else None
        if 'faculty' not in validated_data or validated_data.get('faculty') is None:
            if request is not None and hasattr(request.user, 'faculty_profile'):
                validated_data['faculty'] = request.user.faculty_profile
        schedule = Schedule(**validated_data)
        schedule.full_clean()  # This will run the model's clean method
        schedule.save()
        return schedule
    
    def update(self, instance, validated_data):
        """Update a schedule with model validation."""
        if validated_data.get('location') and not validated_data.get('room'):
            validated_data['room'] = validated_data.get('location')
        # Preserve existing faculty if not provided
        if 'faculty' not in validated_data:
            validated_data['faculty'] = instance.faculty
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.full_clean()  # This will run the model's clean method
        instance.save()
        return instance


class ScheduleListSerializer(serializers.ModelSerializer):
    """Simplified serializer for list views."""
    
    assigned_group_name = serializers.CharField(source='assigned_group.name', read_only=True)
    faculty_name = serializers.CharField(source='faculty.user.full_name', read_only=True)
    
    class Meta:
        model = Schedule
        fields = [
            'id', 'title', 'course_code', 'description',
            'date', 'start_time', 'end_time',
            'location', 'room',
            'is_active',
            'recurring', 'recurrence_pattern', 'recurrence_end_date', 'days_of_week',
            'assigned_group_name', 'faculty_name',
        ]
