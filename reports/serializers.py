from rest_framework import serializers
from attendance.models import AttendanceLog
from students.models import Student, StudentGroup


class AttendanceStatisticsSerializer(serializers.Serializer):
    """Serializer for attendance statistics."""
    total_classes = serializers.IntegerField()
    total_attendance_records = serializers.IntegerField()
    average_attendance_rate = serializers.FloatField()
    

class DailyAttendanceSerializer(serializers.Serializer):
    """Serializer for daily attendance data."""
    date = serializers.DateField()
    total_students = serializers.IntegerField()
    present_count = serializers.IntegerField()
    absent_count = serializers.IntegerField()
    late_count = serializers.IntegerField()
    excused_count = serializers.IntegerField()
    attendance_percentage = serializers.FloatField()


class StudentAbsenceSerializer(serializers.Serializer):
    """Serializer for student absence data."""
    student_id = serializers.CharField(source='student__student_id')
    first_name = serializers.CharField(source='student__user__first_name')
    last_name = serializers.CharField(source='student__user__last_name')
    email = serializers.EmailField(source='student__user__email')
    absence_count = serializers.IntegerField()


class PunctualityDistributionSerializer(serializers.Serializer):
    """Serializer for punctuality distribution data."""
    status = serializers.CharField()
    count = serializers.IntegerField()


class GroupInfoSerializer(serializers.Serializer):
    """Serializer for group information."""
    code = serializers.CharField()
    name = serializers.CharField()
    total_students = serializers.IntegerField()


class ReportPeriodSerializer(serializers.Serializer):
    """Serializer for report period information."""
    from_date = serializers.DateField(source='from')
    to_date = serializers.DateField(source='to')
    group = GroupInfoSerializer()


class AttendanceReportSerializer(serializers.Serializer):
    """Main serializer for attendance report."""
    report_period = ReportPeriodSerializer()
    overall_statistics = AttendanceStatisticsSerializer()
    daily_attendance = DailyAttendanceSerializer(many=True)
    most_absent_students = StudentAbsenceSerializer(many=True)
    punctuality_distribution = PunctualityDistributionSerializer(many=True)


class ChartDatasetSerializer(serializers.Serializer):
    """Serializer for chart dataset."""
    label = serializers.CharField(required=False)
    data = serializers.ListField(child=serializers.FloatField())
    backgroundColor = serializers.CharField(required=False)
    borderColor = serializers.CharField(required=False)
    tension = serializers.FloatField(required=False)


class ChartDataSerializer(serializers.Serializer):
    """Serializer for chart data structure."""
    labels = serializers.ListField(child=serializers.CharField())
    datasets = ChartDatasetSerializer(many=True)


class ChartResponseSerializer(serializers.Serializer):
    """Serializer for chart API response."""
    chart_type = serializers.CharField()
    title = serializers.CharField()
    data = ChartDataSerializer()


class StudentInfoSerializer(serializers.Serializer):
    """Serializer for student information."""
    id = serializers.CharField()
    name = serializers.CharField()
    email = serializers.EmailField()
    group = GroupInfoSerializer()


class AttendanceRecordSerializer(serializers.Serializer):
    """Serializer for individual attendance record."""
    date = serializers.DateField()
    course_code = serializers.CharField()
    course_title = serializers.CharField()
    scheduled_time = serializers.CharField()
    status = serializers.CharField()
    check_in_time = serializers.CharField(allow_null=True)
    check_out_time = serializers.CharField(allow_null=True)
    is_late = serializers.BooleanField()
    is_manual_override = serializers.BooleanField()


class StudentStatisticsSerializer(serializers.Serializer):
    """Serializer for student attendance statistics."""
    total_classes = serializers.IntegerField()
    present = serializers.IntegerField()
    absent = serializers.IntegerField()
    late = serializers.IntegerField()
    excused = serializers.IntegerField()
    attendance_rate = serializers.FloatField()


class StudentAttendanceReportSerializer(serializers.Serializer):
    """Serializer for individual student attendance report."""
    student = StudentInfoSerializer()
    report_period = serializers.DictField()
    statistics = StudentStatisticsSerializer()
    attendance_records = AttendanceRecordSerializer(many=True)
