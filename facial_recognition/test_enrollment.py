#!/usr/bin/env python
"""
Test script for facial enrollment API
Usage: python test_enrollment.py
"""

import requests
import json
import os
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api"

# Test credentials (update with actual admin credentials)
ADMIN_USERNAME = "admin@example.com"
ADMIN_PASSWORD = "admin123"

# Test student ID (update with actual student ID)
STUDENT_ID = "student-uuid-here"

# Test media file path (update with actual file path)
VIDEO_FILE_PATH = "/path/to/test_video.mp4"  # or ZIP file with images


def get_auth_token():
    """Get authentication token"""
    login_url = f"{API_URL}/auth/login/"
    data = {
        "email": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD
    }
    
    response = requests.post(login_url, json=data)
    if response.status_code == 200:
        return response.json()["access"]
    else:
        print(f"Login failed: {response.status_code}")
        print(response.json())
        return None


def test_enrollment_status(token, student_id):
    """Check enrollment status"""
    url = f"{API_URL}/students/{student_id}/enroll/"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(url, headers=headers)
    print("\n=== Enrollment Status ===")
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.json()


def test_enroll_student(token, student_id, media_path):
    """Enroll student with media file"""
    url = f"{API_URL}/students/{student_id}/enroll/"
    headers = {"Authorization": f"Bearer {token}"}
    
    # Check if file exists
    if not os.path.exists(media_path):
        print(f"Error: File not found: {media_path}")
        return None
    
    # Prepare file for upload
    file_name = Path(media_path).name
    with open(media_path, 'rb') as f:
        files = {'media': (file_name, f, 'video/mp4')}  # Adjust MIME type as needed
        
        print(f"\n=== Enrolling Student ===")
        print(f"File: {file_name}")
        print(f"Size: {os.path.getsize(media_path) / 1024 / 1024:.2f} MB")
        
        response = requests.post(url, headers=headers, files=files)
    
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.json()


def test_enrollment_attempts(token, student_id):
    """Get enrollment attempts"""
    url = f"{API_URL}/students/{student_id}/enrollment-attempts/"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(url, headers=headers)
    print("\n=== Enrollment Attempts ===")
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.json()


def test_enrollment_statistics(token):
    """Get enrollment statistics"""
    url = f"{API_URL}/enrollment-statistics/"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(url, headers=headers)
    print("\n=== Enrollment Statistics ===")
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.json()


def test_delete_enrollment(token, student_id):
    """Delete enrollment"""
    url = f"{API_URL}/students/{student_id}/enroll/"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.delete(url, headers=headers)
    print("\n=== Delete Enrollment ===")
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    return response.json()


def main():
    """Main test function"""
    print("=== Facial Enrollment API Test ===")
    
    # Get authentication token
    token = get_auth_token()
    if not token:
        print("Failed to authenticate. Exiting.")
        return
    
    print("Authentication successful!")
    
    # Test 1: Check initial enrollment status
    status = test_enrollment_status(token, STUDENT_ID)
    
    # Test 2: Enroll student (only if not already enrolled)
    if not status.get("enrolled", False):
        if os.path.exists(VIDEO_FILE_PATH):
            enrollment = test_enroll_student(token, STUDENT_ID, VIDEO_FILE_PATH)
        else:
            print(f"\nSkipping enrollment: Video file not found at {VIDEO_FILE_PATH}")
    else:
        print("\nStudent already enrolled.")
    
    # Test 3: Get enrollment attempts
    attempts = test_enrollment_attempts(token, STUDENT_ID)
    
    # Test 4: Get statistics
    stats = test_enrollment_statistics(token)
    
    # Test 5: Optionally delete enrollment (uncomment to test)
    # delete_result = test_delete_enrollment(token, STUDENT_ID)
    
    print("\n=== Test Complete ===")


if __name__ == "__main__":
    main()
