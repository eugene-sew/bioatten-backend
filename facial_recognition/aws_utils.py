import time
import logging
from typing import Dict, Optional
from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image
import io
import numpy as np

from .aws_rekognition import aws_rekognition_service
from .utils import FaceProcessor
from .models import FacialEnrollment

logger = logging.getLogger(__name__)


class AWSFaceProcessor:
    """Enhanced face processor that uses AWS Rekognition."""
    
    def __init__(self):
        self.aws_service = aws_rekognition_service
        self.legacy_processor = FaceProcessor()
        self.provider = 'AWS_REKOGNITION' 
    
    def process_enrollment(self, media_file, file_type: str, student) -> Dict:
        """Process enrollment using AWS Rekognition or legacy system."""
        
        if self.provider == 'AWS_REKOGNITION':
            return self._process_aws_enrollment(media_file, file_type, student)
        else:
            return self._process_legacy_enrollment(media_file, file_type, student)
    
    def _process_aws_enrollment(self, media_file, file_type: str, student) -> Dict:
        """Process enrollment using AWS Rekognition."""
        try:
            # Process media with AWS Rekognition
            results = self.aws_service.process_media_for_enrollment(
                media_file, file_type, student.student_id
            )
            
            if results['faces_detected'] == 0:
                return {
                    'success': False,
                    'error': 'No faces detected in the provided media',
                    'frames_processed': results['frames_processed']
                }
            
            if not results['best_face_id']:
                error_msg = 'No suitable face found for enrollment'
                if results['errors']:
                    # Get the most relevant error message
                    error_msg = results['errors'][-1]  # Last error is usually most relevant
                
                return {
                    'success': False,
                    'error': error_msg,
                    'faces_detected': results['faces_detected'],
                    'frames_processed': results['frames_processed']
                }
            
            # Create thumbnail from the best frame
            thumbnail = self._create_thumbnail_from_results(results)
            
            # Create or update facial enrollment
            enrollment, created = FacialEnrollment.objects.get_or_create(
                student=student,
                defaults={
                    'provider': 'AWS_REKOGNITION',
                    'aws_face_id': results['best_face_id'],
                    'aws_external_image_id': results['face_records'][0]['external_image_id'],
                    'aws_image_id': results['face_records'][0]['image_id'],
                    'face_confidence': results['average_confidence'],
                    'embedding_quality': min(results['average_confidence'] / 100.0, 1.0),
                    'num_faces_detected': results['faces_detected'],
                    'thumbnail': thumbnail,
                    'is_active': True
                }
            )
            
            if not created:
                # Update existing enrollment
                # Delete old face from AWS if it exists
                if enrollment.aws_face_id and enrollment.aws_face_id != results['best_face_id']:
                    try:
                        self.aws_service.delete_faces([enrollment.aws_face_id])
                    except Exception as e:
                        logger.warning(f"Failed to delete old AWS face: {e}")
                
                # Update with new data
                enrollment.provider = 'AWS_REKOGNITION'
                enrollment.aws_face_id = results['best_face_id']
                enrollment.aws_external_image_id = results['face_records'][0]['external_image_id']
                enrollment.aws_image_id = results['face_records'][0]['image_id']
                enrollment.face_confidence = results['average_confidence']
                enrollment.embedding_quality = min(results['average_confidence'] / 100.0, 1.0)
                enrollment.num_faces_detected = results['faces_detected']
                enrollment.thumbnail = thumbnail
                enrollment.is_active = True
                enrollment.save()
            
            return {
                'success': True,
                'enrollment_id': enrollment.id,
                'face_id': results['best_face_id'],
                'confidence': results['average_confidence'],
                'faces_detected': results['faces_detected'],
                'frames_processed': results['frames_processed'],
                'provider': 'AWS_REKOGNITION'
            }
            
        except Exception as e:
            logger.error(f"AWS enrollment processing error: {e}")
            # Provide user-friendly error messages
            error_msg = str(e)
            if "AWS access denied" in error_msg:
                error_msg = "AWS service temporarily unavailable. Please try again later or contact support."
            elif "Collection not found" in error_msg:
                error_msg = "Facial recognition service not properly configured. Please contact support."
            elif "No faces detected" in error_msg:
                error_msg = "No clear face detected in your photo/video. Please ensure good lighting and look directly at the camera."
            elif "Invalid image" in error_msg:
                error_msg = "Invalid image format. Please use a clear photo or video file."
            
            return {
                'success': False,
                'error': error_msg
            }
    
    def _process_legacy_enrollment(self, media_file, file_type: str, student) -> Dict:
        """Process enrollment using legacy DLIB system."""
        try:
            results = self.legacy_processor.process_media_for_enrollment(media_file, file_type)
            
            if results['faces_detected'] == 0:
                return {
                    'success': False,
                    'error': 'No faces detected in the provided media',
                    'frames_processed': results['frames_processed']
                }
            
            # Calculate average embedding
            avg_embedding = self.legacy_processor.calculate_average_embedding(results['embeddings'])
            
            # Create thumbnail
            thumbnail = self.legacy_processor.create_thumbnail(results['face_images'])
            
            # Calculate quality metrics
            quality_metrics = self.legacy_processor.calculate_quality_metrics(results)
            
            # Create or update facial enrollment
            enrollment, created = FacialEnrollment.objects.get_or_create(
                student=student,
                defaults={
                    'provider': 'DLIB',
                    'face_confidence': quality_metrics['average_confidence'],
                    'embedding_quality': quality_metrics['overall_quality'],
                    'num_faces_detected': results['faces_detected'],
                    'thumbnail': thumbnail,
                    'is_active': True
                }
            )
            
            # Set embedding
            enrollment.set_embedding(avg_embedding)
            
            if not created:
                enrollment.provider = 'DLIB'
                enrollment.face_confidence = quality_metrics['average_confidence']
                enrollment.embedding_quality = quality_metrics['overall_quality']
                enrollment.num_faces_detected = results['faces_detected']
                enrollment.thumbnail = thumbnail
                enrollment.is_active = True
                enrollment.set_embedding(avg_embedding)
                enrollment.save()
            
            return {
                'success': True,
                'enrollment_id': enrollment.id,
                'confidence': quality_metrics['average_confidence'],
                'quality_score': quality_metrics['overall_quality'],
                'faces_detected': results['faces_detected'],
                'frames_processed': results['frames_processed'],
                'provider': 'DLIB'
            }
            
        except Exception as e:
            logger.error(f"Legacy enrollment processing error: {e}")
            return {
                'success': False,
                'error': f"Legacy processing failed: {str(e)}"
            }
    
    def verify_face(self, image_data, student) -> Dict:
        """Verify face using AWS Rekognition or legacy system."""
        
        try:
            enrollment = FacialEnrollment.objects.get(student=student, is_active=True)
        except FacialEnrollment.DoesNotExist:
            return {
                'verified': False,
                'confidence': 0.0,
                'error': 'Student not enrolled for facial recognition'
            }
        
        if enrollment.provider == 'AWS_REKOGNITION' and enrollment.aws_face_id:
            return self._verify_aws_face(image_data, student.student_id)
        elif enrollment.provider == 'DLIB' and enrollment.embedding:
            return self._verify_legacy_face(image_data, enrollment)
        else:
            return {
                'verified': False,
                'confidence': 0.0,
                'error': 'Invalid enrollment data'
            }
    
    def _verify_aws_face(self, image_data, student_id: str) -> Dict:
        """Verify face using AWS Rekognition."""
        try:
            result = self.aws_service.verify_face(image_data, student_id)
            return {
                'verified': result['verified'],
                'confidence': result['confidence'],
                'threshold_met': result['threshold_met'],
                'provider': 'AWS_REKOGNITION'
            }
        except Exception as e:
            logger.error(f"AWS face verification error: {e}")
            return {
                'verified': False,
                'confidence': 0.0,
                'error': f"AWS verification failed: {str(e)}",
                'provider': 'AWS_REKOGNITION'
            }
    
    def _verify_legacy_face(self, image_data, enrollment) -> Dict:
        """Verify face using legacy DLIB system."""
        try:
            # Convert image data to numpy array if needed
            if hasattr(image_data, 'read'):
                image_data.seek(0)
                image_bytes = image_data.read()
                image = Image.open(io.BytesIO(image_bytes))
                image_array = np.array(image.convert('RGB'))
            elif isinstance(image_data, np.ndarray):
                image_array = image_data
            else:
                raise ValueError("Unsupported image data type")
            
            # Extract embedding from current image
            current_embedding = self.legacy_processor.extract_face_embedding(image_array)
            
            if current_embedding is None:
                return {
                    'verified': False,
                    'confidence': 0.0,
                    'error': 'No face detected in verification image',
                    'provider': 'DLIB'
                }
            
            # Get stored embedding
            stored_embedding = enrollment.get_embedding()
            
            # Calculate similarity
            similarity = self.legacy_processor.calculate_cosine_similarity(
                current_embedding, stored_embedding
            )
            
            # Convert to percentage and check threshold
            confidence = similarity * 100
            threshold = getattr(settings, 'FACE_VERIFICATION_THRESHOLD', 0.6) * 100
            
            return {
                'verified': confidence >= threshold,
                'confidence': confidence,
                'threshold_met': confidence >= threshold,
                'provider': 'DLIB'
            }
            
        except Exception as e:
            logger.error(f"Legacy face verification error: {e}")
            return {
                'verified': False,
                'confidence': 0.0,
                'error': f"Legacy verification failed: {str(e)}",
                'provider': 'DLIB'
            }
    
    def _create_thumbnail_from_results(self, results) -> ContentFile:
        """Create thumbnail from AWS processing results."""
        # For now, create a simple placeholder thumbnail
        # In a real implementation, you'd extract the best frame and create a thumbnail
        img = Image.new('RGB', (150, 150), color='lightgray')
        
        # Add text indicating AWS enrollment
        try:
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(img)
            draw.text((10, 70), "AWS\nEnrolled", fill='black')
        except:
            pass
        
        thumb_io = io.BytesIO()
        img.save(thumb_io, format='JPEG', quality=85)
        thumb_io.seek(0)
        
        return ContentFile(thumb_io.read(), name='aws_thumbnail.jpg')


# Global instance
aws_face_processor = AWSFaceProcessor()
