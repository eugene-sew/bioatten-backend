from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
import time
import logging

from students.models import Student
from .models import FacialEnrollment, EnrollmentAttempt
from .serializers import (
    FacialEnrollmentSerializer,
    FacialEnrollmentCreateSerializer,
    EnrollmentResponseSerializer,
    EnrollmentAttemptSerializer
)
from .utils import FaceProcessor

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
            # Process the media file
            processor = FaceProcessor()
            results = processor.process_media_for_enrollment(media_file, file_extension)
            
            # Update attempt with results
            attempt.frames_processed = results['frames_processed']
            attempt.faces_detected = results['faces_detected']
            
            # Check if enough faces were detected
            if results['faces_detected'] < 5:
                attempt.status = 'FAILED'
                attempt.error_message = f"Insufficient faces detected: {results['faces_detected']}. Minimum 5 required."
                attempt.processing_time = time.time() - start_time
                attempt.save()
                
                return Response(
                    {
                        'success': False,
                        'message': attempt.error_message,
                        'quality_metrics': processor.calculate_quality_metrics(results),
                        'errors': results['errors']
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Calculate average embedding
            avg_embedding = processor.calculate_average_embedding(results['embeddings'])
            
            # Check for duplicate enrollments (same face on different student accounts)
            duplicate_threshold = 0.95  # Very high threshold to avoid false positives
            existing_enrollments = FacialEnrollment.objects.filter(is_active=True).exclude(student=student)
            
            for existing in existing_enrollments:
                try:
                    existing_embedding = existing.get_embedding()
                    similarity = processor.calculate_cosine_similarity(avg_embedding, existing_embedding)
                    
                    # Log similarity scores for debugging
                    logger.info(f"Similarity check: New enrollment vs {existing.student.user.full_name} (ID: {existing.student.student_id}): {similarity:.3f}")
                    
                    if similarity >= duplicate_threshold:
                        attempt.status = 'FAILED'
                        attempt.error_message = f"This face is already enrolled to another student account (similarity: {similarity:.2f})"
                        attempt.processing_time = time.time() - start_time
                        attempt.save()
                        
                        return Response(
                            {
                                'success': False,
                                'message': f'This face is already enrolled to another student account: {existing.student.user.full_name}',
                                'error_code': 'DUPLICATE_FACE_ENROLLMENT',
                                'similarity_score': similarity,
                                'duplicate_student': {
                                    'name': existing.student.user.full_name,
                                    'student_id': existing.student.student_id
                                }
                            },
                            status=status.HTTP_409_CONFLICT
                        )
                except Exception as e:
                    logger.warning(f"Error checking duplicate enrollment against student {existing.student.student_id}: {e}")
                    continue
            
            # Create thumbnail
            thumbnail = processor.create_thumbnail(results['face_images'])
            
            # Calculate quality metrics
            quality_metrics = processor.calculate_quality_metrics(results)
            
            # Create or update facial enrollment
            with transaction.atomic():
                enrollment, created = FacialEnrollment.objects.update_or_create(
                    student=student,
                    defaults={
                        'face_confidence': quality_metrics['average_confidence'],
                        'embedding_quality': quality_metrics['overall_quality'],
                        'num_faces_detected': results['faces_detected'],
                        'is_active': True
                    }
                )
                
                # Set embedding and thumbnail
                enrollment.set_embedding(avg_embedding)
                enrollment.thumbnail.save(f'student_{student.id}_thumbnail.jpg', thumbnail)
                enrollment.save()
                
                # Update attempt status
                attempt.status = 'SUCCESS'
                attempt.processing_time = time.time() - start_time
                attempt.save()
            
            # Prepare response
            enrollment_serializer = FacialEnrollmentSerializer(enrollment, context={'request': request})
            
            return Response(
                {
                    'success': True,
                    'message': f"Successfully enrolled facial data for {student.user.full_name}",
                    'enrollment': enrollment_serializer.data,
                    'quality_metrics': quality_metrics
                },
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
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
            processor = FaceProcessor()
            results = processor.process_media_for_enrollment(media_file, file_extension)

            attempt.frames_processed = results['frames_processed']
            attempt.faces_detected = results['faces_detected']

            if results['faces_detected'] < 5:
                attempt.status = 'FAILED'
                attempt.error_message = f"Insufficient faces detected: {results['faces_detected']}. Minimum 5 required."
                attempt.processing_time = time.time() - start_time
                attempt.save()

                return Response(
                    {
                        'success': False,
                        'message': attempt.error_message,
                        'quality_metrics': processor.calculate_quality_metrics(results),
                        'errors': results['errors']
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            avg_embedding = processor.calculate_average_embedding(results['embeddings'])
            
            # Check for duplicate enrollments (same face on different student accounts)
            duplicate_threshold = 0.95  # Very high threshold to avoid false positives
            existing_enrollments = FacialEnrollment.objects.filter(is_active=True).exclude(student=student)
            
            for existing in existing_enrollments:
                try:
                    existing_embedding = existing.get_embedding()
                    similarity = processor.calculate_cosine_similarity(avg_embedding, existing_embedding)
                    
                    # Log similarity scores for debugging
                    logger.info(f"Similarity check: New enrollment vs {existing.student.user.full_name} (ID: {existing.student.student_id}): {similarity:.3f}")
                    
                    if similarity >= duplicate_threshold:
                        attempt.status = 'FAILED'
                        attempt.error_message = f"This face is already enrolled to another student account (similarity: {similarity:.2f})"
                        attempt.processing_time = time.time() - start_time
                        attempt.save()
                        
                        return Response(
                            {
                                'success': False,
                                'message': f'This face is already enrolled to another student account: {existing.student.user.full_name}',
                                'error_code': 'DUPLICATE_FACE_ENROLLMENT',
                                'similarity_score': similarity,
                                'duplicate_student': {
                                    'name': existing.student.user.full_name,
                                    'student_id': existing.student.student_id
                                }
                            },
                            status=status.HTTP_409_CONFLICT
                        )
                except Exception as e:
                    logger.warning(f"Error checking duplicate enrollment against student {existing.student.student_id}: {e}")
                    continue
            
            thumbnail = processor.create_thumbnail(results['face_images'])
            quality_metrics = processor.calculate_quality_metrics(results)

            with transaction.atomic():
                enrollment, created = FacialEnrollment.objects.update_or_create(
                    student=student,
                    defaults={
                        'face_confidence': quality_metrics['average_confidence'],
                        'embedding_quality': quality_metrics['overall_quality'],
                        'num_faces_detected': results['faces_detected'],
                        'is_active': True
                    }
                )

                enrollment.set_embedding(avg_embedding)
                enrollment.thumbnail.save(f'student_{student.id}_thumbnail.jpg', thumbnail)
                enrollment.save()

                attempt.status = 'SUCCESS'
                attempt.processing_time = time.time() - start_time
                attempt.save()

            enrollment_serializer = FacialEnrollmentSerializer(enrollment, context={'request': request})

            return Response(
                {
                    'success': True,
                    'message': f"Successfully enrolled facial data for {student.user.full_name}",
                    'enrollment': enrollment_serializer.data,
                    'quality_metrics': quality_metrics
                },
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
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
