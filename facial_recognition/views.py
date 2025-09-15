from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
import logging
import time

from students.models import Student
from .models import FacialEnrollment, EnrollmentAttempt
from .serializers import (
    FacialEnrollmentSerializer,
    FacialEnrollmentCreateSerializer,
    EnrollmentResponseSerializer,
    EnrollmentAttemptSerializer
)
from .utils import FaceProcessor
from .aws_utils import aws_face_processor

logger = logging.getLogger(__name__)


class StudentEnrollmentView(APIView):
    """Handle facial enrollment for students.

    Admin/staff can manage any student.
    A student can manage only their own enrollment.
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request, student_id):
        """Enroll a student's facial data."""
        # Get the student
        student = get_object_or_404(Student, student_id=student_id)
        
        # Permission: admin/staff OR self
        user = request.user
        is_staff = getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False)
        student_profile = getattr(user, 'student_profile', None)
        is_self = bool(student_profile and str(student_profile.student_id) == str(student.student_id))
        if not (is_staff or is_self):
            return Response(
                {"detail": "You do not have permission to perform this action."},
                status=status.HTTP_403_FORBIDDEN,
            )
        
        # Validate input
        serializer = FacialEnrollmentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'message': 'Invalid input data',
                    'errors': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        media_file = serializer.validated_data['media']
        file_extension = media_file.name.split('.')[-1].lower()
        
        # Create enrollment attempt
        attempt = EnrollmentAttempt.objects.create(
            student=student,
            status='PROCESSING'
        )
        
        start_time = time.time()
        
        try:
            # Process the media file using AWS or legacy processor
            results = aws_face_processor.process_enrollment(media_file, file_extension, student)
            
            # Update attempt with results
            attempt.frames_processed = results.get('frames_processed', 0)
            attempt.faces_detected = results.get('faces_detected', 0)
            
            # Check if processing was successful
            if not results['success']:
                attempt.status = 'FAILED'
                attempt.error_message = results.get('error', 'Unknown error during processing')
                attempt.processing_time = time.time() - start_time
                attempt.save()
                
                return Response(
                    {
                        'success': False,
                        'message': attempt.error_message,
                        'provider': results.get('provider', 'UNKNOWN')
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Success case
            attempt.status = 'SUCCESS'
            attempt.processing_time = time.time() - start_time
            attempt.save()
            
            return Response(
                {
                    'success': True,
                    'message': 'Facial enrollment completed successfully',
                    'enrollment_id': results.get('enrollment_id'),
                    'confidence': results.get('confidence'),
                    'faces_detected': results.get('faces_detected'),
                    'frames_processed': results.get('frames_processed'),
                    'provider': results.get('provider')
                },
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            logger.error(f"Error during enrollment: {str(e)}", exc_info=True)
            
            # Update attempt with error
            attempt.status = 'FAILED'
            attempt.error_message = str(e)
            attempt.processing_time = time.time() - start_time
            attempt.save()
            
            return Response(
                {
                    'success': False,
                    'message': 'Enrollment failed due to processing error',
                    'errors': [str(e)]
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EnrollmentStatisticsView(APIView):
    """Get enrollment statistics for admin dashboard."""
    
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        """Get enrollment statistics."""
        try:
            from students.models import Student
            
            # Total students
            total_students = Student.objects.filter(status='ACTIVE').count()
            
            # Total enrollments
            total_enrollments = FacialEnrollment.objects.filter(is_active=True).count()
            
            # AWS vs DLIB enrollments
            aws_enrollments = FacialEnrollment.objects.filter(
                is_active=True, 
                provider='AWS_REKOGNITION'
            ).count()
            dlib_enrollments = FacialEnrollment.objects.filter(
                is_active=True, 
                provider='DLIB'
            ).count()
            
            # Recent enrollment attempts
            recent_attempts = EnrollmentAttempt.objects.filter(
                created_at__gte=timezone.now() - timedelta(days=7)
            ).count()
            
            # Success rate
            successful_attempts = EnrollmentAttempt.objects.filter(
                created_at__gte=timezone.now() - timedelta(days=7),
                status='SUCCESS'
            ).count()
            
            success_rate = (successful_attempts / recent_attempts * 100) if recent_attempts > 0 else 0
            
            # Enrollment rate
            enrollment_rate = (total_enrollments / total_students * 100) if total_students > 0 else 0
            
            return Response({
                'success': True,
                'statistics': {
                    'total_students': total_students,
                    'total_enrollments': total_enrollments,
                    'enrollment_rate': round(enrollment_rate, 1),
                    'aws_enrollments': aws_enrollments,
                    'dlib_enrollments': dlib_enrollments,
                    'recent_attempts': recent_attempts,
                    'success_rate': round(success_rate, 1),
                    'provider_distribution': {
                        'AWS_REKOGNITION': aws_enrollments,
                        'DLIB': dlib_enrollments
                    }
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error getting enrollment statistics: {str(e)}", exc_info=True)
            return Response(
                {
                    'success': False,
                    'error': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StudentEnrollmentView(APIView):
    """Handle facial enrollment for students."""

    permission_classes = [IsAuthenticated]

    def get(self, request, student_id):
        """Get enrollment status for a student."""
        try:
            student = Student.objects.get(student_id=student_id)
        except Student.DoesNotExist:
            return Response(
                {"detail": "Student not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        # Permission: admin/staff OR self
        user = request.user
        is_staff = getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False)
        student_profile = getattr(user, 'student_profile', None)
        is_self = bool(student_profile and str(student_profile.student_id) == str(student.student_id))
        if not (is_staff or is_self):
            return Response(
                {"detail": "You do not have permission to perform this action."},
                status=status.HTTP_403_FORBIDDEN,
            )
        
        try:
            enrollment = FacialEnrollment.objects.get(student=student)
            serializer = FacialEnrollmentSerializer(enrollment, context={'request': request})
            return Response(
                {
                    'success': True,
                    'enrolled': True,
                    'enrollment': serializer.data
                },
                status=status.HTTP_200_OK,
            )
        except FacialEnrollment.DoesNotExist:
            return Response(
                {
                    'success': True,
                    'enrolled': False,
                    'message': 'Student has not been enrolled yet'
                },
                status=status.HTTP_200_OK,
            )
    
    def delete(self, request, student_id):
        """Delete facial enrollment for a student."""
        try:
            student = Student.objects.get(student_id=student_id)
        except Student.DoesNotExist:
            return Response(
                {"detail": "Student not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        # Permission: admin/staff OR self
        user = request.user
        is_staff = getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False)
        student_profile = getattr(user, 'student_profile', None)
        is_self = bool(student_profile and str(student_profile.student_id) == str(student.student_id))
        if not (is_staff or is_self):
            return Response(
                {"detail": "You do not have permission to perform this action."},
                status=status.HTTP_403_FORBIDDEN,
            )
        
        try:
            enrollment = FacialEnrollment.objects.get(student=student)
            enrollment.delete()
            return Response(
                {
                    'success': True,
                    'message': f"Successfully deleted facial enrollment for {student.user.full_name}"
                },
                status=status.HTTP_200_OK,
            )
        except FacialEnrollment.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'message': 'No enrollment found for this student'
                },
                status=status.HTTP_404_NOT_FOUND,
            )


class EnrollmentAttemptsView(APIView):
    """View enrollment attempts for a student."""
    
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request, student_id):
        """Get enrollment attempts for a student."""
        try:
            student = Student.objects.get(student_id=student_id)
        except Student.DoesNotExist:
            return Response(
                {"detail": "Student not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        attempts = EnrollmentAttempt.objects.filter(student=student)
        serializer = EnrollmentAttemptSerializer(attempts, many=True)
        
        return Response(
            {
                'success': True,
                'attempts': serializer.data
            },
            status=status.HTTP_200_OK,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def enrollment_statistics(request):
    """Get overall enrollment statistics."""
    from django.db.models import Count, Avg, Q
    
    stats = {
        'total_students': Student.objects.filter(status='ACTIVE').count(),
        'enrolled_students': FacialEnrollment.objects.filter(is_active=True).count(),
        'enrollment_rate': 0.0,
        'average_quality': FacialEnrollment.objects.filter(is_active=True).aggregate(
            avg_quality=Avg('embedding_quality')
        )['avg_quality'] or 0.0,
        'recent_enrollments': FacialEnrollmentSerializer(
            FacialEnrollment.objects.filter(is_active=True).order_by('-enrollment_date')[:5],
            many=True,
            context={'request': request}
        ).data,
        'failed_attempts_today': EnrollmentAttempt.objects.filter(
            status='FAILED',
            created_at__date=timezone.now().date()
        ).count()
    }
    
    if stats['total_students'] > 0:
        stats['enrollment_rate'] = stats['enrolled_students'] / stats['total_students']
    
    return Response(stats, status=status.HTTP_200_OK)


class SelfEnrollmentView(APIView):
    """Allow an authenticated student to enroll themselves."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        logger.info(f"[SelfEnrollmentView] POST request from user: {request.user.id} ({request.user.email})")
        logger.info(f"[SelfEnrollmentView] User role: {getattr(request.user, 'role', 'NO_ROLE')}")
        logger.info(f"[SelfEnrollmentView] Has student_profile: {hasattr(request.user, 'student_profile')}")
        
        # Try to get student profile
        try:
            student = request.user.student_profile
            logger.info(f"[SelfEnrollmentView] Found student: {student.student_id}")
        except Student.DoesNotExist:
            logger.warning(f"[SelfEnrollmentView] No Student record found for user {request.user.id}")
            # Try to find student by user relationship
            try:
                student = Student.objects.get(user=request.user)
                logger.info(f"[SelfEnrollmentView] Found student via direct query: {student.student_id}")
            except Student.DoesNotExist:
                logger.error(f"[SelfEnrollmentView] No Student record exists for user {request.user.id} (role: {getattr(request.user, 'role', 'NO_ROLE')})")
                return Response(
                    {
                        "detail": "No Student record found for this user. Please contact an administrator to create your student profile.",
                        "error_code": "MISSING_STUDENT_PROFILE",
                        "user_id": request.user.id,
                        "email": request.user.email,
                        "role": getattr(request.user, 'role', None)
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

        serializer = FacialEnrollmentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'message': 'Invalid input data',
                    'errors': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        media_file = serializer.validated_data['media']
        file_extension = media_file.name.split('.')[-1].lower()

        attempt = EnrollmentAttempt.objects.create(
            student=student,
            status='PROCESSING'
        )

        start_time = time.time()

        try:
            # Use AWS Rekognition for enrollment processing
            results = aws_face_processor.process_enrollment(media_file, file_extension, student)

            attempt.frames_processed = results.get('frames_processed', 0)
            attempt.faces_detected = results.get('faces_detected', 0)

            # Check if processing was successful
            if not results['success']:
                attempt.status = 'FAILED'
                attempt.error_message = results.get('error', 'Unknown error during processing')
                attempt.processing_time = time.time() - start_time
                attempt.save()

                return Response(
                    {
                        'success': False,
                        'message': attempt.error_message,
                        'provider': results.get('provider', 'AWS_REKOGNITION')
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Success case
            attempt.status = 'SUCCESS'
            attempt.processing_time = time.time() - start_time
            attempt.save()

            # Get the created enrollment for response
            enrollment = FacialEnrollment.objects.get(id=results['enrollment_id'])
            enrollment_serializer = FacialEnrollmentSerializer(enrollment, context={'request': request})

            return Response(
                {
                    'success': True,
                    'message': f"Successfully enrolled facial data for {student.user.full_name}",
                    'enrollment': enrollment_serializer.data,
                    'enrollment_id': results.get('enrollment_id'),
                    'confidence': results.get('confidence'),
                    'faces_detected': results.get('faces_detected'),
                    'frames_processed': results.get('frames_processed'),
                    'provider': results.get('provider', 'AWS_REKOGNITION')
                },
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            logger.error(f"Error during self-enrollment: {str(e)}", exc_info=True)
            attempt.status = 'FAILED'
            attempt.error_message = str(e)
            attempt.processing_time = time.time() - start_time
            attempt.save()
            return Response(
                {
                    'success': False,
                    'message': 'Enrollment failed due to processing error',
                    'errors': [str(e)]
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SelfEnrollmentStatusView(APIView):
    """Get the authenticated student's enrollment status."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        logger.info(f"[SelfEnrollmentStatusView] GET request from user: {request.user.id} ({request.user.email})")
        logger.info(f"[SelfEnrollmentStatusView] User role: {getattr(request.user, 'role', 'NO_ROLE')}")
        
        # Try to get student profile
        try:
            student = request.user.student_profile
            logger.info(f"[SelfEnrollmentStatusView] Found student via student_profile: {student.student_id}")
        except Student.DoesNotExist:
            logger.warning(f"[SelfEnrollmentStatusView] No Student record found via student_profile for user {request.user.id}")
            # Try to find student by user relationship
            try:
                student = Student.objects.get(user=request.user)
                logger.info(f"[SelfEnrollmentStatusView] Found student via direct query: {student.student_id}")
            except Student.DoesNotExist:
                logger.error(f"[SelfEnrollmentStatusView] No Student record exists for user {request.user.id} (role: {getattr(request.user, 'role', 'NO_ROLE')})")
                return Response(
                    {
                        "detail": "No Student record found for this user. Please contact an administrator to create your student profile.",
                        "error_code": "MISSING_STUDENT_PROFILE",
                        "user_id": request.user.id,
                        "email": request.user.email,
                        "role": getattr(request.user, 'role', None)
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

        try:
            enrollment = FacialEnrollment.objects.get(student=student)
            serializer = FacialEnrollmentSerializer(enrollment, context={'request': request})
            return Response(
                {
                    'success': True,
                    'enrolled': True,
                    'enrollment': serializer.data
                },
                status=status.HTTP_200_OK
            )
        except FacialEnrollment.DoesNotExist:
            return Response(
                {
                    'success': True,
                    'enrolled': False,
                    'message': 'Student has not been enrolled yet'
                },
                status=status.HTTP_200_OK
            )
