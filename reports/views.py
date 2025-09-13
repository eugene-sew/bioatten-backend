from datetime import datetime, timedelta
from django.http import HttpResponse, JsonResponse
from django.db.models import Count, F, Q, Avg, Case, When, IntegerField, FloatField
from django.db.models.functions import Cast
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
import pandas as pd
import json
from io import BytesIO

from attendance.models import AttendanceLog
from students.models import Student, StudentGroup
from schedules.models import Schedule
from authentication.models import User


class AttendanceReportView(APIView):
    """API endpoint for generating attendance reports with aggregations."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        # Get query parameters
        group_code = request.query_params.get('group')
        from_date = request.query_params.get('from')
        to_date = request.query_params.get('to')
        format_type = request.query_params.get('format', 'json')  # json, csv, or excel
        
        # Validate parameters
        if not all([group_code, from_date, to_date]):
            return Response(
                {"error": "Missing required parameters: group, from, to"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Parse dates
            from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
            to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
            
            # Get the student group
            group = StudentGroup.objects.get(code=group_code)
            
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except StudentGroup.DoesNotExist:
            return Response(
                {"error": f"Student group with code '{group_code}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Build the base queryset
        attendance_qs = AttendanceLog.objects.filter(
            schedule__assigned_group=group,
            date__range=[from_date, to_date]
        ).select_related('student__user', 'schedule')
        
        # 1. Daily attendance percentage
        daily_attendance = attendance_qs.values('date').annotate(
            total_students=Count('student', distinct=True),
            present_count=Count(
                Case(
                    When(status__in=['PRESENT', 'LATE'], then=1),
                    output_field=IntegerField()
                )
            ),
            absent_count=Count(
                Case(
                    When(status='ABSENT', then=1),
                    output_field=IntegerField()
                )
            ),
            late_count=Count(
                Case(
                    When(status='LATE', then=1),
                    output_field=IntegerField()
                )
            ),
            excused_count=Count(
                Case(
                    When(status='EXCUSED', then=1),
                    output_field=IntegerField()
                )
            )
        ).annotate(
            attendance_percentage=Cast(
                F('present_count') * 100.0 / F('total_students'),
                FloatField()
            )
        ).order_by('date')
        
        # 2. Most absent students
        student_absences = attendance_qs.filter(
            status='ABSENT'
        ).values(
            'student__student_id',
            'student__user__first_name',
            'student__user__last_name',
            'student__user__email'
        ).annotate(
            absence_count=Count('id')
        ).order_by('-absence_count')[:10]
        
        # 3. Punctuality distribution
        punctuality_dist = attendance_qs.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        # 4. Overall statistics
        total_classes = Schedule.objects.filter(
            assigned_group=group,
            date__range=[from_date, to_date]
        ).count()
        
        total_students = group.students.filter(status='ACTIVE').count()
        
        overall_stats = attendance_qs.aggregate(
            total_records=Count('id'),
            avg_attendance_rate=Avg(
                Case(
                    When(status__in=['PRESENT', 'LATE'], then=1.0),
                    default=0.0,
                    output_field=FloatField()
                )
            ) * 100
        )
        
        # Prepare the response data
        report_data = {
            'report_period': {
                'from': from_date.isoformat(),
                'to': to_date.isoformat(),
                'group': {
                    'code': group.code,
                    'name': group.name,
                    'total_students': total_students
                }
            },
            'overall_statistics': {
                'total_classes': total_classes,
                'total_attendance_records': overall_stats['total_records'],
                'average_attendance_rate': round(overall_stats['avg_attendance_rate'] or 0, 2)
            },
            'daily_attendance': list(daily_attendance),
            'most_absent_students': list(student_absences),
            'punctuality_distribution': list(punctuality_dist)
        }
        
        # Return data based on requested format
        if format_type == 'json':
            return Response(report_data)
        
        elif format_type == 'csv':
            return self._generate_csv_response(report_data, group_code, from_date, to_date)
        
        elif format_type == 'excel':
            return self._generate_excel_response(report_data, group_code, from_date, to_date)
        
        else:
            return Response(
                {"error": "Invalid format. Use 'json', 'csv', or 'excel'"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _generate_csv_response(self, data, group_code, from_date, to_date):
        """Generate CSV file response."""
        # Create a string buffer
        output = BytesIO()
        
        # Daily attendance data
        daily_df = pd.DataFrame(data['daily_attendance'])
        if not daily_df.empty:
            daily_df['date'] = pd.to_datetime(daily_df['date']).dt.strftime('%Y-%m-%d')
            daily_df = daily_df[['date', 'total_students', 'present_count', 'absent_count', 
                               'late_count', 'excused_count', 'attendance_percentage']]
        
        # Most absent students data
        absent_df = pd.DataFrame(data['most_absent_students'])
        if not absent_df.empty:
            absent_df.columns = ['Student ID', 'First Name', 'Last Name', 'Email', 'Absence Count']
        
        # Write to CSV
        csv_content = f"Attendance Report for {group_code}\n"
        csv_content += f"Period: {from_date} to {to_date}\n\n"
        
        csv_content += "Overall Statistics\n"
        csv_content += f"Total Classes: {data['overall_statistics']['total_classes']}\n"
        csv_content += f"Average Attendance Rate: {data['overall_statistics']['average_attendance_rate']}%\n\n"
        
        csv_content += "Daily Attendance\n"
        csv_content += daily_df.to_csv(index=False) if not daily_df.empty else "No data\n"
        csv_content += "\n"
        
        csv_content += "Most Absent Students (Top 10)\n"
        csv_content += absent_df.to_csv(index=False) if not absent_df.empty else "No data\n"
        
        # Create response
        response = HttpResponse(csv_content, content_type='text/csv')
        filename = f"attendance_report_{group_code}_{from_date}_{to_date}.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    def _generate_excel_response(self, data, group_code, from_date, to_date):
        """Generate Excel file response with multiple sheets."""
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Overview sheet
            overview_data = {
                'Metric': [
                    'Report Period',
                    'Group Code',
                    'Group Name',
                    'Total Students',
                    'Total Classes',
                    'Total Records',
                    'Average Attendance Rate'
                ],
                'Value': [
                    f"{from_date} to {to_date}",
                    data['report_period']['group']['code'],
                    data['report_period']['group']['name'],
                    data['report_period']['group']['total_students'],
                    data['overall_statistics']['total_classes'],
                    data['overall_statistics']['total_attendance_records'],
                    f"{data['overall_statistics']['average_attendance_rate']}%"
                ]
            }
            overview_df = pd.DataFrame(overview_data)
            overview_df.to_excel(writer, sheet_name='Overview', index=False)
            
            # Daily attendance sheet
            daily_df = pd.DataFrame(data['daily_attendance'])
            if not daily_df.empty:
                daily_df['date'] = pd.to_datetime(daily_df['date']).dt.strftime('%Y-%m-%d')
                daily_df = daily_df[['date', 'total_students', 'present_count', 'absent_count', 
                                   'late_count', 'excused_count', 'attendance_percentage']]
                daily_df.columns = ['Date', 'Total Students', 'Present', 'Absent', 
                                   'Late', 'Excused', 'Attendance %']
            daily_df.to_excel(writer, sheet_name='Daily Attendance', index=False)
            
            # Most absent students sheet
            absent_df = pd.DataFrame(data['most_absent_students'])
            if not absent_df.empty:
                absent_df.columns = ['Student ID', 'First Name', 'Last Name', 'Email', 'Absence Count']
            absent_df.to_excel(writer, sheet_name='Most Absent Students', index=False)
            
            # Punctuality distribution sheet
            punct_df = pd.DataFrame(data['punctuality_distribution'])
            if not punct_df.empty:
                punct_df.columns = ['Status', 'Count']
            punct_df.to_excel(writer, sheet_name='Punctuality Distribution', index=False)
        
        # Prepare response
        output.seek(0)
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"attendance_report_{group_code}_{from_date}_{to_date}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response


class ChartDataView(APIView):
    """API endpoint for providing chart-ready data for visualization."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        chart_type = request.query_params.get('type', 'daily')
        group_code = request.query_params.get('group')
        from_date = request.query_params.get('from')
        to_date = request.query_params.get('to')
        
        # Validate parameters
        if not all([group_code, from_date, to_date]):
            return Response(
                {"error": "Missing required parameters: group, from, to"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
            to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
            group = StudentGroup.objects.get(code=group_code)
        except (ValueError, StudentGroup.DoesNotExist) as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if chart_type == 'daily':
            # Daily attendance trend line chart data
            data = self._get_daily_attendance_chart_data(group, from_date, to_date)
        elif chart_type == 'status':
            # Attendance status pie chart data
            data = self._get_status_distribution_chart_data(group, from_date, to_date)
        elif chart_type == 'weekly':
            # Weekly attendance bar chart data
            data = self._get_weekly_attendance_chart_data(group, from_date, to_date)
        elif chart_type == 'punctuality':
            # Punctuality timeline chart data
            data = self._get_punctuality_chart_data(group, from_date, to_date)
        else:
            return Response(
                {"error": "Invalid chart type. Use 'daily', 'status', 'weekly', or 'punctuality'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response(data)
    
    def _get_daily_attendance_chart_data(self, group, from_date, to_date):
        """Get data for daily attendance trend line chart."""
        attendance_data = AttendanceLog.objects.filter(
            schedule__assigned_group=group,
            date__range=[from_date, to_date]
        ).values('date').annotate(
            total=Count('student', distinct=True),
            present=Count(
                Case(
                    When(status__in=['PRESENT', 'LATE'], then=1),
                    output_field=IntegerField()
                )
            )
        ).annotate(
            percentage=Cast(F('present') * 100.0 / F('total'), FloatField())
        ).order_by('date')
        
        return {
            'chart_type': 'line',
            'title': 'Daily Attendance Percentage',
            'data': {
                'labels': [item['date'].isoformat() for item in attendance_data],
                'datasets': [{
                    'label': 'Attendance %',
                    'data': [round(item['percentage'], 2) for item in attendance_data],
                    'borderColor': 'rgb(75, 192, 192)',
                    'backgroundColor': 'rgba(75, 192, 192, 0.2)'
                }]
            }
        }
    
    def _get_status_distribution_chart_data(self, group, from_date, to_date):
        """Get data for attendance status pie chart."""
        status_data = AttendanceLog.objects.filter(
            schedule__assigned_group=group,
            date__range=[from_date, to_date]
        ).values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        return {
            'chart_type': 'pie',
            'title': 'Attendance Status Distribution',
            'data': {
                'labels': [item['status'] for item in status_data],
                'datasets': [{
                    'data': [item['count'] for item in status_data],
                    'backgroundColor': [
                        'rgb(75, 192, 192)',   # Present
                        'rgb(255, 99, 132)',   # Absent
                        'rgb(255, 205, 86)',   # Late
                        'rgb(54, 162, 235)'    # Excused
                    ]
                }]
            }
        }
    
    def _get_weekly_attendance_chart_data(self, group, from_date, to_date):
        """Get data for weekly attendance bar chart."""
        # Use raw SQL for week grouping
        from django.db import connection
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    DATE_TRUNC('week', date) as week_start,
                    COUNT(DISTINCT student_id) as total_students,
                    COUNT(CASE WHEN status IN ('PRESENT', 'LATE') THEN 1 END) as present_count,
                    COUNT(CASE WHEN status = 'ABSENT' THEN 1 END) as absent_count,
                    COUNT(CASE WHEN status = 'LATE' THEN 1 END) as late_count
                FROM attendance_logs al
                JOIN schedules s ON al.schedule_id = s.id
                WHERE s.assigned_group_id = %s 
                    AND al.date BETWEEN %s AND %s
                GROUP BY DATE_TRUNC('week', date)
                ORDER BY week_start
            """, [group.id, from_date, to_date])
            
            columns = [col[0] for col in cursor.description]
            weekly_data = [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]
        
        return {
            'chart_type': 'bar',
            'title': 'Weekly Attendance Summary',
            'data': {
                'labels': [f"Week of {item['week_start'].strftime('%Y-%m-%d')}" for item in weekly_data],
                'datasets': [
                    {
                        'label': 'Present',
                        'data': [item['present_count'] for item in weekly_data],
                        'backgroundColor': 'rgb(75, 192, 192)'
                    },
                    {
                        'label': 'Absent',
                        'data': [item['absent_count'] for item in weekly_data],
                        'backgroundColor': 'rgb(255, 99, 132)'
                    },
                    {
                        'label': 'Late',
                        'data': [item['late_count'] for item in weekly_data],
                        'backgroundColor': 'rgb(255, 205, 86)'
                    }
                ]
            }
        }
    
    def _get_punctuality_chart_data(self, group, from_date, to_date):
        """Get data for punctuality timeline chart."""
        # Get check-in times for analysis
        punctuality_data = AttendanceLog.objects.filter(
            schedule__assigned_group=group,
            date__range=[from_date, to_date],
            check_in_time__isnull=False
        ).select_related('schedule').values(
            'date',
            'schedule__start_time',
            'check_in_time'
        )
        
        # Calculate minutes late/early for each record
        processed_data = []
        for record in punctuality_data:
            start_time = record['schedule__start_time']
            check_in = record['check_in_time']
            
            # Calculate difference in minutes
            start_minutes = start_time.hour * 60 + start_time.minute
            check_in_minutes = check_in.hour * 60 + check_in.minute
            diff_minutes = check_in_minutes - start_minutes
            
            processed_data.append({
                'date': record['date'].isoformat(),
                'minutes_diff': diff_minutes
            })
        
        # Group by date and calculate average
        from itertools import groupby
        from operator import itemgetter
        
        grouped_data = []
        for date, group_items in groupby(processed_data, key=itemgetter('date')):
            items = list(group_items)
            avg_diff = sum(item['minutes_diff'] for item in items) / len(items)
            grouped_data.append({
                'date': date,
                'avg_minutes_diff': round(avg_diff, 2)
            })
        
        return {
            'chart_type': 'line',
            'title': 'Average Punctuality (Minutes from Class Start)',
            'data': {
                'labels': [item['date'] for item in grouped_data],
                'datasets': [{
                    'label': 'Minutes Late (+) / Early (-)',
                    'data': [item['avg_minutes_diff'] for item in grouped_data],
                    'borderColor': 'rgb(153, 102, 255)',
                    'backgroundColor': 'rgba(153, 102, 255, 0.2)',
                    'tension': 0.1
                }]
            }
        }


class StudentAttendanceReportView(APIView):
    """API endpoint for individual student attendance reports."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, student_id, *args, **kwargs):
        from_date = request.query_params.get('from')
        to_date = request.query_params.get('to')
        
        try:
            student = Student.objects.get(student_id=student_id)
            
            if from_date:
                from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
            else:
                # Default to current semester start
                from_date = datetime.now().date().replace(month=1, day=1)
            
            if to_date:
                to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
            else:
                to_date = datetime.now().date()
                
        except Student.DoesNotExist:
            return Response(
                {"error": f"Student with ID '{student_id}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get attendance records
        attendance_records = AttendanceLog.objects.filter(
            student=student,
            date__range=[from_date, to_date]
        ).select_related('schedule').order_by('-date', '-schedule__start_time')
        
        # Calculate statistics
        stats = attendance_records.aggregate(
            total_classes=Count('id'),
            present_count=Count(Case(When(status='PRESENT', then=1))),
            absent_count=Count(Case(When(status='ABSENT', then=1))),
            late_count=Count(Case(When(status='LATE', then=1))),
            excused_count=Count(Case(When(status='EXCUSED', then=1)))
        )
        
        # Calculate attendance rate
        if stats['total_classes'] > 0:
            attendance_rate = ((stats['present_count'] + stats['late_count']) / stats['total_classes']) * 100
        else:
            attendance_rate = 0
        
        # Prepare detailed records
        detailed_records = []
        for record in attendance_records:
            detailed_records.append({
                'date': record.date.isoformat(),
                'course_code': record.schedule.course_code,
                'course_title': record.schedule.title,
                'scheduled_time': f"{record.schedule.start_time.strftime('%H:%M')} - {record.schedule.end_time.strftime('%H:%M')}",
                'status': record.status,
                'check_in_time': record.check_in_time.strftime('%H:%M') if record.check_in_time else None,
                'check_out_time': record.check_out_time.strftime('%H:%M') if record.check_out_time else None,
                'is_late': record.is_late,
                'is_manual_override': record.is_manual_override
            })
        
        # Prepare response
        report_data = {
            'student': {
                'id': student.student_id,
                'name': student.user.full_name,
                'email': student.user.email,
                'group': {
                    'code': student.group.code,
                    'name': student.group.name
                }
            },
            'report_period': {
                'from': from_date.isoformat(),
                'to': to_date.isoformat()
            },
            'statistics': {
                'total_classes': stats['total_classes'],
                'present': stats['present_count'],
                'absent': stats['absent_count'],
                'late': stats['late_count'],
                'excused': stats['excused_count'],
                'attendance_rate': round(attendance_rate, 2)
            },
            'attendance_records': detailed_records
        }
        
        return Response(report_data)


class DetailedAttendanceRecordsView(APIView):
    """API endpoint for detailed attendance records with student names."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        # Get query parameters
        group_code = request.query_params.get('group')
        from_date = request.query_params.get('from')
        to_date = request.query_params.get('to')
        
        # Validate parameters
        if not all([group_code, from_date, to_date]):
            return Response(
                {"error": "Missing required parameters: group, from, to"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Parse dates
            from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
            to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
            
            # Get the student group
            group = StudentGroup.objects.get(code=group_code)
            
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except StudentGroup.DoesNotExist:
            return Response(
                {"error": f"Student group with code '{group_code}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get detailed attendance records
        attendance_records = AttendanceLog.objects.filter(
            schedule__assigned_group=group,
            date__range=[from_date, to_date]
        ).select_related('student__user', 'schedule').order_by('-date', 'student__user__last_name')
        
        # Prepare detailed records with student names
        detailed_records = []
        for record in attendance_records:
            detailed_records.append({
                'id': record.id,
                'student_name': record.student.user.full_name,
                'student_id': record.student.student_id,
                'date': record.date.isoformat(),
                'time': record.check_in_time.strftime('%H:%M:%S') if record.check_in_time else 'N/A',
                'status': record.status,
                'method': 'Facial Recognition' if record.face_recognition_confidence else 'Manual',
                'course_code': record.schedule.course_code,
                'course_title': record.schedule.title,
                'is_late': record.is_late,
                'is_manual_override': record.is_manual_override
            })
        
        return Response({
            'success': True,
            'data': detailed_records,
            'count': len(detailed_records)
        })


class DashboardStatsView(APIView):
    """API endpoint for admin dashboard statistics."""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        from authentication.models import User
        from schedules.models import Schedule
        from datetime import date
        
        today = date.today()
        
        # Total users count
        total_users = User.objects.count()
        
        # Total active students
        total_students = Student.objects.filter(status='ACTIVE').count()
        
        # Total courses/groups
        total_courses = StudentGroup.objects.count()
        
        # Today's schedules
        todays_schedules = Schedule.objects.filter(date=today).count()
        
        # Today's attendance statistics
        todays_attendance = AttendanceLog.objects.filter(date=today)
        
        total_attendance_records_today = todays_attendance.count()
        present_today = todays_attendance.filter(status__in=['PRESENT', 'LATE']).count()
        absent_today = todays_attendance.filter(status='ABSENT').count()
        
        # Calculate today's attendance rate
        if total_attendance_records_today > 0:
            attendance_rate_today = round((present_today / total_attendance_records_today) * 100, 1)
        else:
            attendance_rate_today = 0
        
        # Recent enrollments (last 7 days)
        from facial_recognition.models import FacialEnrollment
        from datetime import timedelta
        
        week_ago = today - timedelta(days=7)
        recent_enrollments = FacialEnrollment.objects.filter(
            enrollment_date__gte=week_ago,
            is_active=True
        ).count()
        
        # System-wide statistics
        total_attendance_all_time = AttendanceLog.objects.count()
        total_present_all_time = AttendanceLog.objects.filter(status__in=['PRESENT', 'LATE']).count()
        
        if total_attendance_all_time > 0:
            overall_attendance_rate = round((total_present_all_time / total_attendance_all_time) * 100, 1)
        else:
            overall_attendance_rate = 0
        
        return Response({
            'success': True,
            'data': {
                'users': {
                    'total_users': total_users,
                    'total_students': total_students,
                    'recent_enrollments': recent_enrollments
                },
                'courses': {
                    'total_courses': total_courses,
                    'todays_schedules': todays_schedules
                },
                'attendance': {
                    'today': {
                        'total_records': total_attendance_records_today,
                        'present': present_today,
                        'absent': absent_today,
                        'attendance_rate': attendance_rate_today
                    },
                    'overall': {
                        'total_records': total_attendance_all_time,
                        'present': total_present_all_time,
                        'attendance_rate': overall_attendance_rate
                    }
                },
                'date': today.isoformat()
            }
        })
