#!/usr/bin/env python
"""
Test script for attendance clock-in/clock-out API endpoints.

This script demonstrates how to use the attendance API endpoints with face verification.
"""

import os
import sys
import django
import base64
import json
from io import BytesIO
from PIL import Image
import numpy as np

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bioattend.settings')
django.setup()

from django.contrib.auth import get_user_model
from students.models import Student
from schedules.models import Schedule
from attendance.models import AttendanceLog
from rest_framework.test import APIClient


def create_test_image_base64():
    """Create a test image and return as base64 string."""
    # Create a simple test image (face placeholder)
    img = Image.new('RGB', (224, 224), color='white')
    
    # Convert to base64
    buffer = BytesIO()
    img.save(buffer, format='JPEG')
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    return f"data:image/jpeg;base64,{img_base64}"


def test_clock_in(client, student_user, schedule_id):
    """Test clock-in endpoint."""
    print("\n=== Testing Clock-In ===")
    
    # Login as student
    client.force_authenticate(user=student_user)
    
    # Prepare clock-in data
    data = {
        'snapshot': create_test_image_base64(),
        'schedule_id': schedule_id
    }
    
    # Make clock-in request
    response = client.post('/api/attendance/clock_in/', data, format='json')
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.data, indent=2)}")
    
    return response


def test_clock_out(client, student_user, schedule_id):
    """Test clock-out endpoint."""
    print("\n=== Testing Clock-Out ===")
    
    # Login as student
    client.force_authenticate(user=student_user)
    
    # Prepare clock-out data
    data = {
        'snapshot': create_test_image_base64(),
        'schedule_id': schedule_id
    }
    
    # Make clock-out request
    response = client.post('/api/attendance/clock_out/', data, format='json')
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.data, indent=2)}")
    
    return response


def test_attendance_status(client, student_user, schedule_id):
    """Test attendance status endpoint."""
    print("\n=== Testing Attendance Status ===")
    
    # Login as student
    client.force_authenticate(user=student_user)
    
    # Get attendance status
    response = client.get(f'/api/attendance/status/{schedule_id}/')
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.data, indent=2)}")
    
    return response


def main():
    """Run attendance API tests."""
    print("Starting Attendance API Tests...")
    
    # Create test client
    client = APIClient()
    
    # Get or create test student user
    User = get_user_model()
    try:
        student_user = User.objects.get(email='test.student@bioattend.com')
        student = student_user.student_profile
        print(f"Using existing test student: {student_user.email}")
    except User.DoesNotExist:
        print("Test student not found. Please create a test student first.")
        return
    
    # Get first available schedule
    schedule = Schedule.objects.first()
    if not schedule:
        print("No schedules found. Please create a schedule first.")
        return
    
    print(f"Using schedule: {schedule.course_code} - {schedule.course_name}")
    
    # Test attendance status (before clock-in)
    test_attendance_status(client, student_user, schedule.id)
    
    # Test clock-in
    clock_in_response = test_clock_in(client, student_user, schedule.id)
    
    # Note: In a real scenario, face verification would fail without proper enrollment
    # This test will show the face verification failure response
    
    if clock_in_response.status_code == 201:
        # If clock-in successful, test clock-out
        test_clock_out(client, student_user, schedule.id)
        
        # Test attendance status (after clock-out)
        test_attendance_status(client, student_user, schedule.id)
    
    print("\n=== Test Complete ===")


if __name__ == '__main__':
    main()
