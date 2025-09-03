from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from datetime import date, time, timedelta
from students.models import StudentGroup
from faculty.models import Faculty
from .models import Schedule

User = get_user_model()


class ScheduleModelTest(TestCase):
    """Test cases for the Schedule model."""
    
    def setUp(self):
        # Create test users
        self.faculty_user = User.objects.create_user(
            username='faculty1',
            email='faculty@test.com',
            password='testpass',
            role=User.FACULTY,
            first_name='John',
            last_name='Doe'
        )
        
        # Create test data
        self.group = StudentGroup.objects.create(
            name='Biology Year 1',
            code='BIO1',
            academic_year='2024-2025',
            semester='Spring'
        )
        
        self.faculty = Faculty.objects.create(
            user=self.faculty_user,
            faculty_id='FAC001',
            department='Biology',
            designation='PROFESSOR',
            join_date=date.today()
        )
    
    def test_schedule_creation(self):
        """Test creating a valid schedule."""
        schedule = Schedule.objects.create(
            title='Introduction to Biology',
            course_code='BIO101',
            date=date.today() + timedelta(days=1),
            start_time=time(9, 0),
            end_time=time(10, 30),
            clock_in_opens_at=time(8, 45),
            clock_in_closes_at=time(9, 15),
            assigned_group=self.group,
            faculty=self.faculty,
            room='Lab 201'
        )
        
        self.assertEqual(schedule.title, 'Introduction to Biology')
        self.assertEqual(schedule.course_code, 'BIO101')
        self.assertIsNotNone(schedule.created_at)
    
    def test_schedule_validation(self):
        """Test schedule validation rules."""
        schedule = Schedule(
            title='Test Class',
            course_code='TEST101',
            date=date.today(),
            start_time=time(10, 0),
            end_time=time(9, 0),  # Invalid: end before start
            clock_in_opens_at=time(9, 45),
            clock_in_closes_at=time(10, 15),
            assigned_group=self.group,
            faculty=self.faculty
        )
        
        with self.assertRaises(Exception):
            schedule.full_clean()
    
    def test_clock_in_window_validation(self):
        """Test clock-in window validation."""
        schedule = Schedule(
            title='Test Class',
            course_code='TEST101',
            date=date.today(),
            start_time=time(9, 0),
            end_time=time(10, 0),
            clock_in_opens_at=time(10, 0),  # Invalid: opens after start
            clock_in_closes_at=time(10, 30),
            assigned_group=self.group,
            faculty=self.faculty
        )
        
        with self.assertRaises(Exception):
            schedule.full_clean()


class ScheduleAPITest(APITestCase):
    """Test cases for Schedule API endpoints."""
    
    def setUp(self):
        # Create test users
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='adminpass'
        )
        
        self.faculty_user = User.objects.create_user(
            username='faculty1',
            email='faculty@test.com',
            password='testpass',
            role=User.FACULTY,
            first_name='John',
            last_name='Doe'
        )
        
        # Create test data
        self.group = StudentGroup.objects.create(
            name='Biology Year 1',
            code='BIO1',
            academic_year='2024-2025',
            semester='Spring'
        )
        
        self.faculty = Faculty.objects.create(
            user=self.faculty_user,
            faculty_id='FAC001',
            department='Biology',
            designation='PROFESSOR',
            join_date=date.today()
        )
        
        # Authenticate as admin
        self.client.force_authenticate(user=self.admin_user)
    
    def test_create_schedule(self):
        """Test creating a schedule via API."""
        data = {
            'title': 'Introduction to Biology',
            'course_code': 'BIO101',
            'date': str(date.today() + timedelta(days=1)),
            'start_time': '09:00:00',
            'end_time': '10:30:00',
            'clock_in_opens_at': '08:45:00',
            'clock_in_closes_at': '09:15:00',
            'assigned_group': self.group.id,
            'faculty': self.faculty.id,
            'room': 'Lab 201',
            'description': 'First lecture'
        }
        
        response = self.client.post('/api/schedules/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Schedule.objects.count(), 1)
        
        schedule = Schedule.objects.first()
        self.assertEqual(schedule.title, 'Introduction to Biology')
    
    def test_list_schedules(self):
        """Test listing schedules."""
        # Create test schedules
        Schedule.objects.create(
            title='Class 1',
            course_code='BIO101',
            date=date.today(),
            start_time=time(9, 0),
            end_time=time(10, 0),
            clock_in_opens_at=time(8, 45),
            clock_in_closes_at=time(9, 15),
            assigned_group=self.group,
            faculty=self.faculty
        )
        
        Schedule.objects.create(
            title='Class 2',
            course_code='BIO102',
            date=date.today() + timedelta(days=1),
            start_time=time(11, 0),
            end_time=time(12, 0),
            clock_in_opens_at=time(10, 45),
            clock_in_closes_at=time(11, 15),
            assigned_group=self.group,
            faculty=self.faculty
        )
        
        response = self.client.get('/api/schedules/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
    
    def test_filter_by_date_range(self):
        """Test filtering schedules by date range."""
        today = date.today()
        
        # Create schedules for different dates
        Schedule.objects.create(
            title='Today Class',
            course_code='BIO101',
            date=today,
            start_time=time(9, 0),
            end_time=time(10, 0),
            clock_in_opens_at=time(8, 45),
            clock_in_closes_at=time(9, 15),
            assigned_group=self.group,
            faculty=self.faculty
        )
        
        Schedule.objects.create(
            title='Future Class',
            course_code='BIO102',
            date=today + timedelta(days=7),
            start_time=time(9, 0),
            end_time=time(10, 0),
            clock_in_opens_at=time(8, 45),
            clock_in_closes_at=time(9, 15),
            assigned_group=self.group,
            faculty=self.faculty
        )
        
        # Filter for next 3 days
        response = self.client.get(
            '/api/schedules/',
            {'date_from': str(today), 'date_to': str(today + timedelta(days=3))}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Today Class')
    
    def test_filter_by_group(self):
        """Test filtering schedules by group."""
        # Create another group
        group2 = StudentGroup.objects.create(
            name='Chemistry Year 1',
            code='CHEM1',
            academic_year='2024-2025',
            semester='Spring'
        )
        
        # Create schedules for different groups
        Schedule.objects.create(
            title='Biology Class',
            course_code='BIO101',
            date=date.today(),
            start_time=time(9, 0),
            end_time=time(10, 0),
            clock_in_opens_at=time(8, 45),
            clock_in_closes_at=time(9, 15),
            assigned_group=self.group,
            faculty=self.faculty
        )
        
        Schedule.objects.create(
            title='Chemistry Class',
            course_code='CHEM101',
            date=date.today(),
            start_time=time(11, 0),
            end_time=time(12, 0),
            clock_in_opens_at=time(10, 45),
            clock_in_closes_at=time(11, 15),
            assigned_group=group2,
            faculty=self.faculty
        )
        
        # Filter by biology group
        response = self.client.get('/api/schedules/', {'group': self.group.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Biology Class')
    
    def test_today_endpoint(self):
        """Test the today's schedules endpoint."""
        # Create a schedule for today
        Schedule.objects.create(
            title='Today Class',
            course_code='BIO101',
            date=date.today(),
            start_time=time(9, 0),
            end_time=time(10, 0),
            clock_in_opens_at=time(8, 45),
            clock_in_closes_at=time(9, 15),
            assigned_group=self.group,
            faculty=self.faculty
        )
        
        # Create a schedule for tomorrow
        Schedule.objects.create(
            title='Tomorrow Class',
            course_code='BIO102',
            date=date.today() + timedelta(days=1),
            start_time=time(9, 0),
            end_time=time(10, 0),
            clock_in_opens_at=time(8, 45),
            clock_in_closes_at=time(9, 15),
            assigned_group=self.group,
            faculty=self.faculty
        )
        
        response = self.client.get('/api/schedules/today/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Today Class')
    
    def test_validation_errors(self):
        """Test API validation errors."""
        # Invalid time order
        data = {
            'title': 'Invalid Schedule',
            'course_code': 'TEST101',
            'date': str(date.today()),
            'start_time': '10:00:00',
            'end_time': '09:00:00',  # End before start
            'clock_in_opens_at': '09:45:00',
            'clock_in_closes_at': '10:15:00',
            'assigned_group': self.group.id,
            'faculty': self.faculty.id
        }
        
        response = self.client.post('/api/schedules/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('end_time', response.data)
