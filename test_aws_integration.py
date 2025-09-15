#!/usr/bin/env python
"""
Test script for AWS Rekognition integration.
This script tests the basic functionality of the AWS Rekognition service.
"""

import os
import sys
import django
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bioattend.settings')
django.setup()

from facial_recognition.aws_rekognition import AWSRekognitionService
from facial_recognition.aws_utils import aws_face_processor
from django.conf import settings


def test_aws_configuration():
    """Test AWS configuration and credentials."""
    print("=== Testing AWS Configuration ===")
    
    # Check if AWS is configured
    aws_access_key = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
    aws_secret_key = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
    aws_region = getattr(settings, 'AWS_REGION', None)
    collection_id = getattr(settings, 'AWS_REKOGNITION_COLLECTION_ID', None)
    provider = getattr(settings, 'FACIAL_RECOGNITION_PROVIDER', 'DLIB')
    
    print(f"AWS Access Key ID: {'Set' if aws_access_key else 'Not set'}")
    print(f"AWS Secret Access Key: {'Set' if aws_secret_key else 'Not set'}")
    print(f"AWS Region: {aws_region}")
    print(f"Collection ID: {collection_id}")
    print(f"Provider: {provider}")
    
    if not all([aws_access_key, aws_secret_key, aws_region, collection_id]):
        print("❌ AWS configuration incomplete. Please set all required environment variables.")
        return False
    
    print("✅ AWS configuration appears complete.")
    return True


def test_aws_connection():
    """Test connection to AWS Rekognition service."""
    print("\n=== Testing AWS Connection ===")
    
    try:
        aws_service = AWSRekognitionService()
        
        # Test basic connection by listing collections
        collections = aws_service.list_collections()
        print(f"✅ Successfully connected to AWS Rekognition")
        print(f"Available collections: {collections}")
        
        # Check if our collection exists
        collection_id = settings.AWS_REKOGNITION_COLLECTION_ID
        if collection_id in collections:
            print(f"✅ Collection '{collection_id}' exists")
            
            # Get collection info
            faces = aws_service.list_faces(max_results=5)
            print(f"Collection contains {len(faces)} faces")
        else:
            print(f"⚠️  Collection '{collection_id}' does not exist")
            print("Creating collection...")
            try:
                aws_service.create_collection()
                print(f"✅ Successfully created collection '{collection_id}'")
            except Exception as e:
                print(f"❌ Failed to create collection: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to connect to AWS Rekognition: {e}")
        return False


def test_face_processor():
    """Test the AWS face processor initialization."""
    print("\n=== Testing Face Processor ===")
    
    try:
        processor = aws_face_processor
        print(f"Face processor provider: {processor.provider}")
        
        if processor.provider == 'AWS_REKOGNITION':
            print("✅ AWS Face Processor initialized successfully")
            print(f"AWS Service available: {processor.aws_service is not None}")
        else:
            print(f"⚠️  Using legacy provider: {processor.provider}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to initialize face processor: {e}")
        return False


def test_facial_recognition_status():
    """Test the facial recognition status endpoint logic."""
    print("\n=== Testing Facial Recognition Status ===")
    
    try:
        from facial_recognition.models import FacialEnrollment
        
        # Get enrollment statistics
        total_enrollments = FacialEnrollment.objects.filter(is_active=True).count()
        aws_enrollments = FacialEnrollment.objects.filter(
            is_active=True, 
            provider='AWS_REKOGNITION'
        ).count()
        legacy_enrollments = FacialEnrollment.objects.filter(
            is_active=True, 
            provider='DLIB'
        ).count()
        
        print(f"Total active enrollments: {total_enrollments}")
        print(f"AWS Rekognition enrollments: {aws_enrollments}")
        print(f"Legacy DLIB enrollments: {legacy_enrollments}")
        
        provider = aws_face_processor.provider
        print(f"Current provider: {provider}")
        
        # Test AWS connection if using AWS
        aws_status = 'Not configured'
        if provider == 'AWS_REKOGNITION':
            try:
                aws_face_processor.aws_service.list_faces(max_results=1)
                aws_status = 'Connected'
                print("✅ AWS connection test successful")
            except Exception as e:
                aws_status = f'Error: {str(e)}'
                print(f"❌ AWS connection test failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Status test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("AWS Rekognition Integration Test")
    print("=" * 50)
    
    tests = [
        test_aws_configuration,
        test_aws_connection,
        test_face_processor,
        test_facial_recognition_status
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("Test Summary:")
    print(f"Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("✅ All tests passed! AWS Rekognition integration is ready.")
    else:
        print("❌ Some tests failed. Please check the configuration and try again.")
        print("\nTroubleshooting:")
        print("1. Ensure AWS credentials are set in environment variables")
        print("2. Verify AWS region is correct")
        print("3. Check AWS IAM permissions for Rekognition")
        print("4. Ensure collection ID is unique and valid")


if __name__ == '__main__':
    main()
