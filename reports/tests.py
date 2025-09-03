from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import date, time, timedelta
from authentication.models import User
from students.models import Student, StudentGroup
from faculty.models import Faculty
from schedules.models import Schedule
from attendance.models import AttendanceLog


class AttendanceReportViewTestCase(APITestCase):
    """Test cases for AttendanceReportView."""
    
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            email='faculty@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Faculty',
            role=User.FACULTY
        )
        
        # Create test faculty
        self.faculty = Faculty.objects.create(
            user=self.user,
            faculty_id='FAC001',
            department='Computer Science'
        )
        
        # Create test group
        self.group = StudentGroup.objects.create(
            name='Test Group',
            code='TG001',
            description='Test group for unit tests',
            academic_year='2024-2025',
            semester='Fall'
        )
        
        # Create test students
        self.students = []
        for i in range(5):
            student_user = User.objects.create_user(
                email=f'student{i}@test.com',
                password='testpass123',
                first_name=f'Student{i}',
                last_name='Test',
                role=User.STUDENT
            )
            student = Student.objects.create(
                user=student_user,
                student_id=f'STU00{i}',
                group=self.group,
                enrollment_date=date(2024, 1, 1)
            )
            self.students.append(student)
        
        # Create test schedule
        self.schedule = Schedule.objects.create(
            title='Test Lecture',
            course_code='CS101',
            date=date.today(),
            start_time=time(9, 0),
            end_time=time(10, 30),
            clock_in_opens_at=time(8, 45),
            clock_in_closes_at=time(9, 15),
            assigned_group=self.group,
            faculty=self.faculty,
            room='Room 101'
        )
        
        # Create attendance logs
        statuses = ['PRESENT', 'PRESENT', 'ABSENT', 'LATE', 'EXCUSED']
        for i, student in enumerate(self.students):
            AttendanceLog.objects.create(
                student=student,
                schedule=self.schedule,
                date=self.schedule.date,
                status=statuses[i],
                check_in_time=time(9, 5) if statuses[i] in ['PRESENT', 'LATE'] else None
            )
        
        # Authenticate the test client
        self.client.force_authenticate(user=self.user)
    
    def test_attendance_report_json(self):
        """Test getting attendance report in JSON format."""
        url = reverse('reports:attendance-report')
        response = self.client.get(url, {
            'group': self.group.code,
            'from': date.today().isoformat(),
            'to': date.today().isoformat(),
            'format': 'json'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('report_period', response.data)
        self.assertIn('overall_statistics', response.data)
        self.assertIn('daily_attendance', response.data)
        self.assertIn('most_absent_students', response.data)
        self.assertIn('punctuality_distribution', response.data)
        
        # Check statistics
        stats = response.data['overall_statistics']
        self.assertEqual(stats['total_classes'], 1)
        self.assertEqual(stats['total_attendance_records'], 5)
        
    def test_attendance_report_csv(self):
        """Test getting attendance report in CSV format."""
        url = reverse('reports:attendance-report')
        response = self.client.get(url, {
            'group': self.group.code,
            'from': date.today().isoformat(),
            'to': date.today().isoformat(),
            'format': 'csv'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment', response['Content-Disposition'])
        
    def test_attendance_report_excel(self):
        """Test getting attendance report in Excel format."""
        url = reverse('reports:attendance-report')
        response = self.client.get(url, {
            'group': self.group.code,
            'from': date.today().isoformat(),
            'to': date.today().isoformat(),
            'format': 'excel'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        self.assertIn('attachment', response['Content-Disposition'])
    
    def test_missing_parameters(self):
        """Test error handling for missing parameters."""
        url = reverse('reports:attendance-report')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_invalid_group(self):
        """Test error handling for invalid group code."""
        url = reverse('reports:attendance-report')
        response = self.client.get(url, {
            'group': 'INVALID',
            'from': date.today().isoformat(),
            'to': date.today().isoformat()
        })
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)


class ChartDataViewTestCase(APITestCase):
    """Test cases for ChartDataView."""
    
    def setUp(self):
        # Create test data similar to AttendanceReportViewTestCase
        self.user = User.objects.create_user(
            email='faculty@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Faculty',
            role=User.FACULTY
        )
        
        self.group = StudentGroup.objects.create(
            name='Test Group',
            code='TG001',
            description='Test group',
            academic_year='2024-2025',
            semester='Fall'
        )
        
        self.client.force_authenticate(user=self.user)
    
    def test_daily_chart_data(self):
        """Test getting daily attendance chart data."""
        url = reverse('reports:chart-data')
        response = self.client.get(url, {
            'type': 'daily',
            'group': self.group.code,
            'from': date.today().isoformat(),
            'to': date.today().isoformat()
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['chart_type'], 'line')
        self.assertIn('data', response.data)
        self.assertIn('labels', response.data['data'])
        self.assertIn('datasets', response.data['data'])
    
    def test_status_distribution_chart_data(self):
        """Test getting status distribution chart data."""
        url = reverse('reports:chart-data')
        response = self.client.get(url, {
            'type': 'status',
            'group': self.group.code,
            'from': date.today().isoformat(),
            'to': date.today().isoformat()
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['chart_type'], 'pie')
    
    def test_invalid_chart_type(self):
        """Test error handling for invalid chart type."""
        url = reverse('reports:chart-data')
        response = self.client.get(url, {
            'type': 'invalid',
            'group': self.group.code,
            'from': date.today().isoformat(),
            'to': date.today().isoformat()
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)


class StudentAttendanceReportViewTestCase(APITestCase):
    """Test cases for StudentAttendanceReportView."""
    
    def setUp(self):
        # Create test data
        self.user = User.objects.create_user(
            email='student@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Student',
            role=User.STUDENT
        )
        
        self.group = StudentGroup.objects.create(
            name='Test Group',
            code='TG001',
            description='Test group',
            academic_year='2024-2025',
            semester='Fall'
        )
        
        self.student = Student.objects.create(
            user=self.user,
            student_id='STU001',
            group=self.group,
            enrollment_date=date(2024, 1, 1)
        )
        
        self.client.force_authenticate(user=self.user)
    
    def test_student_report(self):
        """Test getting individual student report."""
        url = reverse('reports:student-report', args=[self.student.student_id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('student', response.data)
        self.assertIn('report_period', response.data)
        self.assertIn('statistics', response.data)
        self.assertIn('attendance_records', response.data)
        
        # Check student info
        student_data = response.data['student']
        self.assertEqual(student_data['id'], self.student.student_id)
        self.assertEqual(student_data['name'], self.user.full_name)
    
    def test_student_not_found(self):
        """Test error handling for non-existent student."""
        url = reverse('reports:student-report', args=['INVALID'])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)
    
    def test_date_range_filtering(self):
        """Test filtering by date range."""
        url = reverse('reports:student-report', args=[self.student.student_id])
        
        # Test with specific date range
        from_date = date.today() - timedelta(days=30)
        to_date = date.today()
        
        response = self.client.get(url, {
            'from': from_date.isoformat(),
            'to': to_date.isoformat()
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that report period matches requested dates
        period = response.data['report_period']
        self.assertEqual(period['from'], from_date.isoformat())
        self.assertEqual(period['to'], to_date.isoformat())
