from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
import logging
import base64
import io
from PIL import Image
import numpy as np

from students.models import Student
from .models import FacialEnrollment
from .aws_utils import aws_face_processor

logger = logging.getLogger(__name__)


class FacialVerificationView(APIView):
    """Handle facial verification for attendance."""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Verify a face against enrolled students."""
        
        # Get image data from request
        image_data = request.data.get('image')
        student_id = request.data.get('student_id')
        
        if not image_data:
            return Response(
                {
                    'success': False,
                    'error': 'No image data provided'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not student_id:
            return Response(
                {
                    'success': False,
                    'error': 'No student ID provided'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get student
            student = Student.objects.get(student_id=student_id)
            
            # Check if student is enrolled
            try:
                enrollment = FacialEnrollment.objects.get(student=student, is_active=True)
            except FacialEnrollment.DoesNotExist:
                return Response(
                    {
                        'success': False,
                        'verified': False,
                        'error': 'Student not enrolled for facial recognition'
                    },
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Process image data
            if isinstance(image_data, str):
                # Base64 encoded image
                try:
                    if image_data.startswith('data:image'):
                        # Remove data URL prefix
                        image_data = image_data.split(',')[1]
                    
                    image_bytes = base64.b64decode(image_data)
                    image_file = io.BytesIO(image_bytes)
                except Exception as e:
                    return Response(
                        {
                            'success': False,
                            'error': f'Invalid image data: {str(e)}'
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # File upload
                image_file = image_data
            
            # Verify face using AWS or legacy processor
            verification_result = aws_face_processor.verify_face(image_file, student)
            
            return Response(
                {
                    'success': True,
                    'verified': verification_result['verified'],
                    'confidence': verification_result['confidence'],
                    'threshold_met': verification_result.get('threshold_met', False),
                    'provider': verification_result.get('provider', 'UNKNOWN'),
                    'student': {
                        'student_id': student.student_id,
                        'name': student.user.full_name,
                        'email': student.user.email
                    }
                },
                status=status.HTTP_200_OK
            )
            
        except Student.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'verified': False,
                    'error': 'Student not found'
                },
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Facial verification error: {str(e)}", exc_info=True)
            return Response(
                {
                    'success': False,
                    'verified': False,
                    'error': f'Verification failed: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BulkFacialVerificationView(APIView):
    """Handle bulk facial verification for attendance (identify unknown face)."""
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """Identify a face against all enrolled students."""
        
        # Get image data from request
        image_data = request.data.get('image')
        max_results = int(request.data.get('max_results', 5))
        
        if not image_data:
            return Response(
                {
                    'success': False,
                    'error': 'No image data provided'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Process image data
            if isinstance(image_data, str):
                # Base64 encoded image
                try:
                    if image_data.startswith('data:image'):
                        # Remove data URL prefix
                        image_data = image_data.split(',')[1]
                    
                    image_bytes = base64.b64decode(image_data)
                    image_file = io.BytesIO(image_bytes)
                except Exception as e:
                    return Response(
                        {
                            'success': False,
                            'error': f'Invalid image data: {str(e)}'
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # File upload
                image_file = image_data
            
            # Use AWS Rekognition to search for faces
            if aws_face_processor.provider == 'AWS_REKOGNITION':
                try:
                    matches = aws_face_processor.aws_service.search_faces_by_image(
                        image_file, max_faces=max_results
                    )
                    
                    # Convert matches to student information
                    results = []
                    for match in matches:
                        # Extract student ID from external_image_id
                        external_id = match.get('external_image_id', '')
                        if external_id and 'student_' in external_id:
                            try:
                                student_id = external_id.split('student_')[1].split('_')[0]
                                student = Student.objects.get(student_id=student_id)
                                
                                results.append({
                                    'student_id': student.student_id,
                                    'name': student.user.full_name,
                                    'email': student.user.email,
                                    'confidence': match['similarity'],
                                    'face_id': match['face_id']
                                })
                            except (Student.DoesNotExist, IndexError):
                                continue
                    
                    return Response(
                        {
                            'success': True,
                            'matches': results,
                            'provider': 'AWS_REKOGNITION'
                        },
                        status=status.HTTP_200_OK
                    )
                    
                except Exception as e:
                    logger.error(f"AWS bulk verification error: {str(e)}")
                    return Response(
                        {
                            'success': False,
                            'error': f'AWS verification failed: {str(e)}'
                        },
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            
            else:
                # Legacy DLIB implementation for bulk verification
                return Response(
                    {
                        'success': False,
                        'error': 'Bulk verification not implemented for legacy DLIB system'
                    },
                    status=status.HTTP_501_NOT_IMPLEMENTED
                )
            
        except Exception as e:
            logger.error(f"Bulk facial verification error: {str(e)}", exc_info=True)
            return Response(
                {
                    'success': False,
                    'error': f'Verification failed: {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def facial_recognition_status(request):
    """Get facial recognition system status."""
    
    try:
        # Check provider configuration
        provider = aws_face_processor.provider
        
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
        
        # Test AWS connection if using AWS
        aws_status = 'Not configured'
        if provider == 'AWS_REKOGNITION':
            try:
                # Try to list faces to test connection
                aws_face_processor.aws_service.list_faces(max_results=1)
                aws_status = 'Connected'
            except Exception as e:
                aws_status = f'Error: {str(e)}'
        
        return Response(
            {
                'success': True,
                'provider': provider,
                'aws_status': aws_status,
                'enrollments': {
                    'total': total_enrollments,
                    'aws_rekognition': aws_enrollments,
                    'legacy_dlib': legacy_enrollments
                }
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        return Response(
            {
                'success': False,
                'error': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
