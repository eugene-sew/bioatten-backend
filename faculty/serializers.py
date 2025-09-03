from rest_framework import serializers
from .models import Faculty
from students.serializers import StudentGroupMiniSerializer
from students.models import StudentGroup


class FacultySerializer(serializers.ModelSerializer):
    groups = serializers.PrimaryKeyRelatedField(
        many=True, queryset=StudentGroup.objects.all(), required=False
    )
    groups_detail = StudentGroupMiniSerializer(source='groups', many=True, read_only=True)

    class Meta:
        model = Faculty
        fields = [
            'id', 'faculty_id', 'department', 'designation', 'office_location',
            'phone_number', 'join_date', 'status', 'user', 'groups', 'groups_detail'
        ]
        read_only_fields = ['faculty_id', 'user']
