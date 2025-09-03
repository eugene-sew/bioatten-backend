import numpy as np
import base64
import io
import cv2
from PIL import Image
from typing import Optional, Tuple, Dict
import logging
from facial_recognition.utils import FaceProcessor
from facial_recognition.models import FacialEnrollment

logger = logging.getLogger(__name__)


class FaceVerificationService:
    """Service for verifying faces against enrolled student embeddings."""
    
    def __init__(self, similarity_threshold: float = 0.6):
        self.similarity_threshold = similarity_threshold
        self.face_processor = FaceProcessor()
    
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
    
    def calculate_cosine_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings."""
        # Ensure embeddings are normalized
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        embedding1_norm = embedding1 / norm1
        embedding2_norm = embedding2 / norm2
        
        # Calculate cosine similarity
        similarity = np.dot(embedding1_norm, embedding2_norm)
        
        return float(similarity)
    
    def verify_face(self, snapshot_base64: str, student_id: int) -> Dict:
        """
        Verify a face snapshot against a student's enrolled embedding.
        
        Returns:
            Dict containing:
                - verified: bool - Whether verification was successful
                - confidence: float - Confidence score (0-1)
                - message: str - Status message
                - embedding: np.ndarray - The extracted embedding (if successful)
        """
        result = {
            'verified': False,
            'confidence': 0.0,
            'message': 'Verification failed',
            'embedding': None
        }
        
        try:
            # Get student's enrollment
            try:
                enrollment = FacialEnrollment.objects.get(
                    student_id=student_id,
                    is_active=True
                )
            except FacialEnrollment.DoesNotExist:
                result['message'] = 'Student has no active facial enrollment'
                return result
            
            # Decode the snapshot
            snapshot_image = self.decode_base64_image(snapshot_base64)
            
            # Detect faces in snapshot
            faces = self.face_processor.detect_faces(snapshot_image)
            
            if not faces:
                result['message'] = 'No face detected in snapshot'
                return result
            
            if len(faces) > 1:
                result['message'] = 'Multiple faces detected in snapshot'
                return result
            
            # Get the single face
            face = faces[0]
            
            # Crop and align the face
            face_img = self.face_processor.align_and_crop_face(
                snapshot_image, 
                face['box']
            )
            
            if face_img is None:
                result['message'] = 'Failed to process detected face'
                return result
            
            # Extract embedding from snapshot
            snapshot_embedding = self.face_processor.extract_face_embedding(face_img)
            
            if snapshot_embedding is None:
                result['message'] = 'Failed to extract face embedding from snapshot'
                return result
            
            # Get stored embedding
            stored_embedding = enrollment.get_embedding()
            
            # Calculate similarity
            similarity = self.calculate_cosine_similarity(snapshot_embedding, stored_embedding)
            
            # Check against threshold
            if similarity >= self.similarity_threshold:
                result['verified'] = True
                result['confidence'] = similarity
                result['message'] = 'Face verified successfully'
                result['embedding'] = snapshot_embedding
            else:
                result['confidence'] = similarity
                result['message'] = f'Face similarity ({similarity:.2f}) below threshold ({self.similarity_threshold})'
            
            logger.info(f"Face verification for student {student_id}: similarity={similarity:.3f}, verified={result['verified']}")
            
        except Exception as e:
            logger.error(f"Error during face verification: {str(e)}", exc_info=True)
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
