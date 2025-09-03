from rest_framework import serializers
from .models import Student, StudentGroup


class StudentGroupMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentGroup
        fields = ("id", "name", "code", "academic_year", "semester")


class StudentListSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    full_name = serializers.SerializerMethodField()
    department = serializers.SerializerMethodField()
    group = StudentGroupMiniSerializer(read_only=True)

    class Meta:
        model = Student
        fields = (
            "id",
            "student_id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "group",
            "status",
            "enrollment_date",
            "graduation_date",
            "department",
        )

    def get_full_name(self, obj):
        return obj.user.full_name

    def get_department(self, obj):
        request = self.context.get("request")
        if request and hasattr(request.user, "faculty_profile"):
            return request.user.faculty_profile.department
        return None
