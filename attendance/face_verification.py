import numpy as np
import base64
import io
import cv2
from PIL import Image
from typing import Optional, Tuple, Dict
import logging
from facial_recognition.aws_rekognition import AWSRekognitionService
from facial_recognition.models import FacialEnrollment

logger = logging.getLogger(__name__)


class FaceVerificationService:
    """Service for verifying faces against enrolled students using AWS Rekognition."""
    
    def __init__(self, similarity_threshold: float = 80.0):
        self.similarity_threshold = similarity_threshold
        self.aws_service = AWSRekognitionService()
    
    def decode_base64_image(self, base64_string: str) -> np.ndarray:
        """Decode base64 string to numpy array image."""
        try:
            # Remove data URL prefix if present
            if base64_string.startswith('data:image'):
                base64_string = base64_string.split(',')[1]
            
            # Decode base64
            img_data = base64.b64decode(base64_string)
            
            # Convert to PIL Image
            img = Image.open(io.BytesIO(img_data))
            
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Convert to numpy array
            return np.array(img)
            
        except Exception as e:
            logger.error(f"Error decoding base64 image: {str(e)}")
            raise ValueError(f"Failed to decode image: {str(e)}")
    
    def _get_student_external_id(self, student_id: int) -> str:
        """Generate external ID for AWS Rekognition face collection."""
        return f"student_{student_id}"
    
    def verify_face(self, snapshot_base64: str, student_id: int) -> Dict:
        """
        Verify a face snapshot against a student's enrolled face using AWS Rekognition.
        
        Returns:
            Dict containing:
                - verified: bool - Whether verification was successful
                - confidence: float - Confidence score (0-100)
                - message: str - Status message
        """
        result = {
            'verified': False,
            'confidence': 0.0,
            'message': 'Verification failed'
        }
        
        try:
            # Check if student has enrollment record
            try:
                enrollment = FacialEnrollment.objects.get(
                    student_id=student_id,
                    is_active=True
                )
            except FacialEnrollment.DoesNotExist:
                result['message'] = 'Student has no active facial enrollment'
                return result
            
            # Decode the snapshot image
            snapshot_image = self.decode_base64_image(snapshot_base64)
            
            # Convert to PIL Image for AWS Rekognition
            pil_image = Image.fromarray(snapshot_image)
            
            # Use AWS Rekognition to search for matching faces
            matches = self.aws_service.search_faces_by_image(
                image_data=pil_image,
                max_faces=1
            )
            
            if not matches:
                # Check if student is enrolled but face not found
                if enrollment.provider == 'AWS_REKOGNITION' and enrollment.aws_face_id:
                    result['message'] = 'Face not recognized. Please ensure good lighting and look directly at the camera, or contact support if the issue persists.'
                else:
                    result['message'] = 'You are not enrolled for facial recognition. Please complete your facial enrollment first.'
                return result
            
            # Check if the match is for this student
            best_match = matches[0]
            expected_external_id = self._get_student_external_id(student_id)
            
            if best_match['external_image_id'] == expected_external_id:
                similarity = best_match['similarity']
                
                if similarity >= self.similarity_threshold:
                    result['verified'] = True
                    result['confidence'] = float(similarity)
                    result['message'] = 'Face verification successful'
                else:
                    result['confidence'] = float(similarity)
                    result['message'] = 'Face recognition confidence too low. Please ensure good lighting and look directly at the camera.'
            else:
                result['message'] = 'Face recognized but belongs to a different student. Please ensure you are using your own account.'
            
            return result
            
        except Exception as e:
            logger.error(f"AWS Rekognition verification error: {str(e)}")
            result['message'] = f'Verification error: {str(e)}'
            return result
    
    def save_verification_image(self, image_array: np.ndarray, attendance_log_id: int, 
                              is_clock_in: bool = True) -> Optional[str]:
        """Save verification image for audit purposes."""
        try:
            # Convert numpy array to PIL Image
            img = Image.fromarray(image_array)
            
            # Create filename
            prefix = "clock_in" if is_clock_in else "clock_out"
            filename = f"attendance/{prefix}_{attendance_log_id}.jpg"
            
            # Save to media directory
            from django.conf import settings
            import os
            
            filepath = os.path.join(settings.MEDIA_ROOT, filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            img.save(filepath, quality=85)
            
            return filename
            
        except Exception as e:
            logger.error(f"Error saving verification image: {str(e)}")
            return None
