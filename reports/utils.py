from datetime import datetime, timedelta
import pandas as pd
from django.db.models import Count, Q, Avg, F
from attendance.models import AttendanceLog
from students.models import Student, StudentGroup
from schedules.models import Schedule


class AttendanceReportGenerator:
    """Utility class for generating comprehensive attendance reports."""
    
    def __init__(self, group, from_date, to_date):
        self.group = group
        self.from_date = from_date
        self.to_date = to_date
        
    def generate_summary_stats(self):
        """Generate summary statistics for the attendance report."""
        attendance_logs = AttendanceLog.objects.filter(
            schedule__assigned_group=self.group,
            date__range=[self.from_date, self.to_date]
        )
        
        total_students = self.group.students.filter(status='ACTIVE').count()
        total_classes = Schedule.objects.filter(
            assigned_group=self.group,
            date__range=[self.from_date, self.to_date]
        ).count()
        
        # Calculate attendance rates by status
        status_counts = attendance_logs.values('status').annotate(count=Count('id'))
        status_dict = {item['status']: item['count'] for item in status_counts}
        
        total_records = sum(status_dict.values())
        attendance_rate = 0
        if total_records > 0:
            present_and_late = status_dict.get('PRESENT', 0) + status_dict.get('LATE', 0)
            attendance_rate = (present_and_late / total_records) * 100
        
        return {
            'total_students': total_students,
            'total_classes': total_classes,
            'total_records': total_records,
            'attendance_rate': round(attendance_rate, 2),
            'status_breakdown': status_dict
        }
    
    def generate_student_rankings(self):
        """Generate student rankings based on attendance."""
        attendance_logs = AttendanceLog.objects.filter(
            schedule__assigned_group=self.group,
            date__range=[self.from_date, self.to_date]
        )
        
        # Best attendance (most present + late)
        best_attendance = attendance_logs.filter(
            status__in=['PRESENT', 'LATE']
        ).values(
            'student__student_id',
            'student__user__first_name',
            'student__user__last_name'
        ).annotate(
            attendance_count=Count('id')
        ).order_by('-attendance_count')[:10]
        
        # Most punctual (highest ratio of PRESENT vs LATE)
        punctuality_data = attendance_logs.filter(
            status__in=['PRESENT', 'LATE']
        ).values('student').annotate(
            present_count=Count('id', filter=Q(status='PRESENT')),
            late_count=Count('id', filter=Q(status='LATE')),
            total=F('present_count') + F('late_count')
        ).annotate(
            punctuality_score=F('present_count') * 100.0 / F('total')
        )
        
        # Convert to DataFrame for easier processing
        punctuality_df = pd.DataFrame(list(punctuality_data))
        if not punctuality_df.empty:
            punctuality_df = punctuality_df.sort_values('punctuality_score', ascending=False).head(10)
            
            # Get student details
            student_ids = punctuality_df['student'].tolist()
            students = Student.objects.filter(id__in=student_ids).select_related('user')
            student_dict = {s.id: s for s in students}
            
            most_punctual = []
            for _, row in punctuality_df.iterrows():
                student = student_dict.get(row['student'])
                if student:
                    most_punctual.append({
                        'student_id': student.student_id,
                        'name': student.user.full_name,
                        'punctuality_score': round(row['punctuality_score'], 2),
                        'present_count': int(row['present_count']),
                        'late_count': int(row['late_count'])
                    })
        else:
            most_punctual = []
        
        return {
            'best_attendance': list(best_attendance),
            'most_punctual': most_punctual
        }
    
    def generate_weekly_trends(self):
        """Generate weekly attendance trends."""
        attendance_logs = AttendanceLog.objects.filter(
            schedule__assigned_group=self.group,
            date__range=[self.from_date, self.to_date]
        ).values('date', 'status')
        
        # Convert to DataFrame
        df = pd.DataFrame(list(attendance_logs))
        if df.empty:
            return []
        
        # Add week information
        df['date'] = pd.to_datetime(df['date'])
        df['week'] = df['date'].dt.isocalendar().week
        df['year'] = df['date'].dt.year
        
        # Group by week and calculate statistics
        weekly_stats = df.groupby(['year', 'week', 'status']).size().unstack(fill_value=0)
        weekly_stats['total'] = weekly_stats.sum(axis=1)
        weekly_stats['attendance_rate'] = (
            (weekly_stats.get('PRESENT', 0) + weekly_stats.get('LATE', 0)) / 
            weekly_stats['total'] * 100
        )
        
        # Format for response
        weekly_trends = []
        for (year, week), row in weekly_stats.iterrows():
            # Get the Monday of that week
            week_start = datetime.strptime(f'{year}-W{week}-1', '%Y-W%W-%w').date()
            weekly_trends.append({
                'week_start': week_start.isoformat(),
                'week_number': week,
                'present': int(row.get('PRESENT', 0)),
                'absent': int(row.get('ABSENT', 0)),
                'late': int(row.get('LATE', 0)),
                'excused': int(row.get('EXCUSED', 0)),
                'total': int(row['total']),
                'attendance_rate': round(row['attendance_rate'], 2)
            })
        
        return weekly_trends
    
    def generate_course_wise_stats(self):
        """Generate attendance statistics by course."""
        attendance_logs = AttendanceLog.objects.filter(
            schedule__assigned_group=self.group,
            date__range=[self.from_date, self.to_date]
        ).select_related('schedule')
        
        # Group by course code
        course_stats = {}
        for log in attendance_logs:
            course_code = log.schedule.course_code
            if course_code not in course_stats:
                course_stats[course_code] = {
                    'course_code': course_code,
                    'course_title': log.schedule.title,
                    'total': 0,
                    'present': 0,
                    'absent': 0,
                    'late': 0,
                    'excused': 0
                }
            
            course_stats[course_code]['total'] += 1
            if log.status == 'PRESENT':
                course_stats[course_code]['present'] += 1
            elif log.status == 'ABSENT':
                course_stats[course_code]['absent'] += 1
            elif log.status == 'LATE':
                course_stats[course_code]['late'] += 1
            elif log.status == 'EXCUSED':
                course_stats[course_code]['excused'] += 1
        
        # Calculate attendance rates
        for course in course_stats.values():
            if course['total'] > 0:
                course['attendance_rate'] = round(
                    ((course['present'] + course['late']) / course['total']) * 100, 2
                )
            else:
                course['attendance_rate'] = 0
        
        return list(course_stats.values())


def generate_attendance_certificate(student, from_date, to_date):
    """Generate an attendance certificate for a student."""
    attendance_logs = AttendanceLog.objects.filter(
        student=student,
        date__range=[from_date, to_date]
    )
    
    stats = attendance_logs.aggregate(
        total_classes=Count('id'),
        present_count=Count('id', filter=Q(status='PRESENT')),
        late_count=Count('id', filter=Q(status='LATE'))
    )
    
    attended = stats['present_count'] + stats['late_count']
    attendance_percentage = 0
    if stats['total_classes'] > 0:
        attendance_percentage = (attended / stats['total_classes']) * 100
    
    certificate_data = {
        'student_name': student.user.full_name,
        'student_id': student.student_id,
        'group': student.group.name,
        'period': f"{from_date} to {to_date}",
        'total_classes': stats['total_classes'],
        'classes_attended': attended,
        'attendance_percentage': round(attendance_percentage, 2),
        'generated_on': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return certificate_data


def export_attendance_data(queryset, format='csv'):
    """Export attendance data in various formats."""
    # Convert queryset to DataFrame
    data = list(queryset.values(
        'date',
        'student__student_id',
        'student__user__first_name',
        'student__user__last_name',
        'schedule__course_code',
        'schedule__title',
        'status',
        'check_in_time',
        'check_out_time',
        'is_manual_override'
    ))
    
    df = pd.DataFrame(data)
    
    # Rename columns for better readability
    column_mapping = {
        'student__student_id': 'Student ID',
        'student__user__first_name': 'First Name',
        'student__user__last_name': 'Last Name',
        'schedule__course_code': 'Course Code',
        'schedule__title': 'Course Title',
        'status': 'Attendance Status',
        'check_in_time': 'Check-in Time',
        'check_out_time': 'Check-out Time',
        'is_manual_override': 'Manual Override'
    }
    df.rename(columns=column_mapping, inplace=True)
    
    # Format date
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
    
    # Format times
    for time_col in ['Check-in Time', 'Check-out Time']:
        if time_col in df.columns:
            df[time_col] = pd.to_datetime(df[time_col], format='%H:%M:%S').dt.strftime('%H:%M')
    
    return df
