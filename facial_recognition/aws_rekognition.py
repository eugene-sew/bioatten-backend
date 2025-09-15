import boto3
import numpy as np
from PIL import Image
import io
import logging
import time
from typing import List, Dict
from botocore.exceptions import ClientError
from django.conf import settings

logger = logging.getLogger(__name__)


class AWSRekognitionService:
    """AWS Rekognition service wrapper for facial enrollment and verification."""
    
    def __init__(self):
        """Initialize AWS Rekognition client."""
        self.client = boto3.client(
            'rekognition',
            aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', 'AKIAUH5KX4IS72YY6UPJ'),
            aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', '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'),
            region_name=getattr(settings, 'AWS_REGION', 'us-east-1')
        )
        self.collection_id = getattr(settings, 'AWS_REKOGNITION_COLLECTION_ID', 'bioattend-faces')
        self.similarity_threshold = getattr(settings, 'AWS_REKOGNITION_SIMILARITY_THRESHOLD', 80.0)
        
        # Ensure collection exists
        self._ensure_collection_exists()
    
    def _ensure_collection_exists(self):
        """Ensure the face collection exists, create if it doesn't."""
        try:
            self.client.describe_collection(CollectionId=self.collection_id)
            logger.info(f"Face collection '{self.collection_id}' exists")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                self.create_collection()
    
    def create_collection(self):
        """Create a new collection for storing faces."""
        try:
            response = self.client.create_collection(CollectionId=self.collection_id)
            logger.info(f"Created collection: {self.collection_id}")
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceAlreadyExistsException':
                logger.info(f"Collection {self.collection_id} already exists")
                return {'StatusCode': 200}
            else:
                logger.error(f"Error creating collection: {e}")
                raise
    
    def list_collections(self):
        """List all available collections."""
        try:
            response = self.client.list_collections()
            return response.get('CollectionIds', [])
        except ClientError as e:
            logger.error(f"Error listing collections: {e}")
            raise
    
    def _prepare_image_bytes(self, image_data) -> bytes:
        """Convert image data to bytes format for AWS Rekognition."""
        if isinstance(image_data, np.ndarray):
            # Convert numpy array to PIL Image
            if image_data.dtype != np.uint8:
                image_data = (image_data * 255).astype(np.uint8)
            
            pil_image = Image.fromarray(image_data)
            
            # Convert to bytes
            img_byte_arr = io.BytesIO()
            pil_image.save(img_byte_arr, format='JPEG', quality=95)
            return img_byte_arr.getvalue()
        
        elif isinstance(image_data, Image.Image):
            # PIL Image object
            img_byte_arr = io.BytesIO()
            # Ensure RGB mode for JPEG
            if image_data.mode != 'RGB':
                image_data = image_data.convert('RGB')
            image_data.save(img_byte_arr, format='JPEG', quality=95)
            return img_byte_arr.getvalue()
        
        elif hasattr(image_data, 'read'):
            # File-like object
            image_data.seek(0)
            return image_data.read()
        
        elif isinstance(image_data, bytes):
            return image_data
        
        else:
            raise ValueError(f"Unsupported image data type: {type(image_data)}")
    
    def detect_faces(self, image_data) -> List[Dict]:
        """Detect faces in an image using AWS Rekognition."""
        try:
            image_bytes = self._prepare_image_bytes(image_data)
            
            response = self.client.detect_faces(
                Image={'Bytes': image_bytes},
                Attributes=['ALL']
            )
            
            faces = []
            for face_detail in response['FaceDetails']:
                bbox = face_detail['BoundingBox']
                faces.append({
                    'box': (
                        int(bbox['Left'] * 1000),  # Convert to pixel coordinates (assuming 1000px width)
                        int(bbox['Top'] * 1000),
                        int((bbox['Left'] + bbox['Width']) * 1000),
                        int((bbox['Top'] + bbox['Height']) * 1000)
                    ),
                    'confidence': face_detail['Confidence'],
                    'quality': face_detail.get('Quality', {}).get('Sharpness', 0.5),
                    'emotions': face_detail.get('Emotions', []),
                    'age_range': face_detail.get('AgeRange', {}),
                    'gender': face_detail.get('Gender', {})
                })
            
            return faces
            
        except ClientError as e:
            logger.error(f"AWS Rekognition detect_faces error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error detecting faces: {e}")
            raise
    
    def index_face(self, image_data, external_image_id: str) -> Dict:
        """Index a face in the AWS Rekognition collection."""
        try:
            image_bytes = self._prepare_image_bytes(image_data)
            
            response = self.client.index_faces(
                CollectionId=self.collection_id,
                Image={'Bytes': image_bytes},
                ExternalImageId=external_image_id,
                MaxFaces=1,
                QualityFilter='AUTO'
            )
            
            if not response['FaceRecords']:
                logger.error(f"No faces detected for indexing. Response: {response}")
                raise ValueError("No faces detected for indexing")
            
            face_record = response['FaceRecords'][0]
            return {
                'face_id': face_record['Face']['FaceId'],
                'external_image_id': face_record['Face']['ExternalImageId'],
                'confidence': face_record['Face']['Confidence'],
                'bounding_box': face_record['Face']['BoundingBox'],
                'image_id': face_record['Face']['ImageId']
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"AWS Rekognition index_faces ClientError: {error_code} - {error_message}")
            
            if error_code == 'InvalidParameterException':
                raise ValueError(f"Invalid image data or parameters: {error_message}")
            elif error_code == 'ResourceNotFoundException':
                raise ValueError(f"Collection not found: {self.collection_id}")
            elif error_code == 'AccessDeniedException':
                raise ValueError("AWS access denied. Please check your credentials and permissions.")
            else:
                raise ValueError(f"AWS Rekognition error: {error_message}")
                
        except Exception as e:
            logger.error(f"Error indexing face: {e}")
            raise ValueError(f"Face indexing failed: {str(e)}")
    
    def search_faces_by_image(self, image_data, max_faces: int = 1) -> List[Dict]:
        """Search for faces in the collection using an image."""
        try:
            image_bytes = self._prepare_image_bytes(image_data)
            
            response = self.client.search_faces_by_image(
                CollectionId=self.collection_id,
                Image={'Bytes': image_bytes},
                MaxFaces=max_faces,
                FaceMatchThreshold=self.similarity_threshold
            )
            
            matches = []
            for face_match in response['FaceMatches']:
                matches.append({
                    'face_id': face_match['Face']['FaceId'],
                    'external_image_id': face_match['Face']['ExternalImageId'],
                    'similarity': face_match['Similarity'],
                    'confidence': face_match['Face']['Confidence']
                })
            
            return matches
            
        except ClientError as e:
            logger.error(f"AWS Rekognition search_faces_by_image error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error searching faces: {e}")
            raise
    
    def delete_faces(self, face_ids: List[str]) -> Dict:
        """Delete faces from the collection."""
        try:
            response = self.client.delete_faces(
                CollectionId=self.collection_id,
                FaceIds=face_ids
            )
            
            return {
                'deleted_faces': response['DeletedFaces'],
                'unprocessed_face_ids': response.get('UnprocessedFaceIds', [])
            }
            
        except ClientError as e:
            logger.error(f"AWS Rekognition delete_faces error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error deleting faces: {e}")
            raise
    
    def list_faces(self, max_results: int = 100) -> List[Dict]:
        """List all faces in the collection."""
        try:
            response = self.client.list_faces(
                CollectionId=self.collection_id,
                MaxResults=max_results
            )
            
            faces = []
            for face in response['Faces']:
                faces.append({
                    'face_id': face['FaceId'],
                    'external_image_id': face.get('ExternalImageId'),
                    'confidence': face['Confidence'],
                    'image_id': face['ImageId']
                })
            
            return faces
            
        except ClientError as e:
            logger.error(f"AWS Rekognition list_faces error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error listing faces: {e}")
            raise
    
    def process_media_for_enrollment(self, media_file, file_type: str, student_id: str) -> Dict:
        """Process video or image archive for facial enrollment using AWS Rekognition."""
        results = {
            'frames_processed': 0,
            'faces_detected': 0,
            'face_records': [],
            'errors': [],
            'best_face_id': None,
            'average_confidence': 0.0
        }
        
        try:
            # Use existing frame extraction logic
            from .utils import FaceProcessor
            processor = FaceProcessor()
            
            # Extract frames/images
            if file_type in ['mp4', 'avi', 'mov']:
                # Create temporary file for video processing
                import tempfile
                import os
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_type}') as tmp_file:
                    for chunk in media_file.chunks():
                        tmp_file.write(chunk)
                    tmp_file_path = tmp_file.name
                
                try:
                    frames = processor.extract_frames_from_video(tmp_file_path)
                finally:
                    os.unlink(tmp_file_path)
            else:  # ZIP archive
                frames = processor.extract_images_from_zip(media_file)
            
            results['frames_processed'] = len(frames)
            
            # Process frames with AWS Rekognition
            confidences = []
            best_confidence = 0
            best_frame_idx = 0
            
            for i, frame in enumerate(frames):
                try:
                    # Detect faces using AWS Rekognition
                    faces = self.detect_faces(frame)
                    
                    if faces:
                        # Use the face with highest confidence
                        best_face = max(faces, key=lambda x: x['confidence'])
                        confidences.append(best_face['confidence'])
                        results['faces_detected'] += 1
                        
                        # Track best frame for indexing
                        if best_face['confidence'] > best_confidence:
                            best_confidence = best_face['confidence']
                            best_frame_idx = i
                
                except Exception as e:
                    results['errors'].append(f"Error processing frame {i}: {str(e)}")
                    logger.error(f"Error processing frame {i}: {e}")
            
            # Index the best face if we found any
            if results['faces_detected'] > 0:
                try:
                    external_image_id = f"student_{student_id}_{int(time.time())}"
                    face_record = self.index_face(frames[best_frame_idx], external_image_id)
                    results['best_face_id'] = face_record['face_id']
                    results['face_records'].append(face_record)
                    results['average_confidence'] = sum(confidences) / len(confidences)
                    
                except Exception as e:
                    results['errors'].append(f"Error indexing best face: {str(e)}")
                    logger.error(f"Error indexing best face: {e}")
        
        except Exception as e:
            results['errors'].append(f"Error processing media: {str(e)}")
            logger.error(f"Error processing media: {e}")
        
        return results
    
    def verify_face(self, image_data, student_id: str) -> Dict:
        """Verify a face against enrolled faces for a student."""
        try:
            # Search for matching faces
            matches = self.search_faces_by_image(image_data, max_faces=5)
            
            # Filter matches by student ID (external_image_id contains student ID)
            student_matches = [
                match for match in matches 
                if match['external_image_id'] and f"student_{student_id}" in match['external_image_id']
            ]
            
            if student_matches:
                # Return the best match
                best_match = max(student_matches, key=lambda x: x['similarity'])
                return {
                    'verified': True,
                    'confidence': best_match['similarity'],
                    'face_id': best_match['face_id'],
                    'threshold_met': best_match['similarity'] >= self.similarity_threshold
                }
            else:
                return {
                    'verified': False,
                    'confidence': 0.0,
                    'face_id': None,
                    'threshold_met': False
                }
                
        except Exception as e:
            logger.error(f"Error verifying face: {e}")
            return {
                'verified': False,
                'confidence': 0.0,
                'face_id': None,
                'threshold_met': False,
                'error': str(e)
            }


# Global instance
aws_rekognition_service = AWSRekognitionService()
