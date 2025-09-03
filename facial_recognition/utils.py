import cv2
import numpy as np
import tempfile
import zipfile
import os
from typing import List, Tuple, Dict, Optional
from PIL import Image
import io
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile
import logging

logger = logging.getLogger(__name__)


class FaceProcessor:
    """Handles face detection, alignment, and embedding extraction."""
    
    def __init__(self):
        # We'll use face_recognition (dlib) for face detection
        pass
    
    def extract_frames_from_video(self, video_path: str, max_frames: int = 30) -> List[np.ndarray]:
        """Extract frames from video file."""
        frames = []
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError("Could not open video file")
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Calculate frame interval to get evenly spaced frames
        interval = max(1, total_frames // max_frames)
        
        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % interval == 0:
                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(frame_rgb)
                
                if len(frames) >= max_frames:
                    break
            
            frame_count += 1
        
        cap.release()
        return frames
    
    def extract_images_from_zip(self, zip_file) -> List[np.ndarray]:
        """Extract images from ZIP archive."""
        images = []
        
        with zipfile.ZipFile(zip_file, 'r') as zf:
            for filename in sorted(zf.namelist()):
                if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                    try:
                        with zf.open(filename) as img_file:
                            img = Image.open(img_file)
                            img_array = np.array(img.convert('RGB'))
                            images.append(img_array)
                    except Exception as e:
                        logger.warning(f"Could not process image {filename}: {e}")
        
        return images
    
    def detect_faces(self, image: np.ndarray) -> List[Dict]:
        """Detect faces using face_recognition (dlib)."""
        import face_recognition
        # Use CNN model for better accuracy when available
        try:
            face_locations = face_recognition.face_locations(image, model='cnn')
        except:
            # Fallback to HOG model if CNN fails (e.g., no GPU)
            face_locations = face_recognition.face_locations(image, model='hog')
        
        faces = []
        for (top, right, bottom, left) in face_locations:
            faces.append({
                'box': (left, top, right, bottom),
                'confidence': 0.95  # Default confidence for dlib
            })
        
        return faces
    
    
    def align_and_crop_face(self, image: np.ndarray, face_box: Tuple[int, int, int, int], 
                           padding: float = 0.2) -> Optional[np.ndarray]:
        """Align and crop face from image."""
        left, top, right, bottom = face_box
        
        # Add padding around face
        width = right - left
        height = bottom - top
        
        pad_w = int(width * padding)
        pad_h = int(height * padding)
        
        # Ensure coordinates are within image bounds
        left = max(0, left - pad_w)
        top = max(0, top - pad_h)
        right = min(image.shape[1], right + pad_w)
        bottom = min(image.shape[0], bottom + pad_h)
        
        # Crop face
        face_img = image[top:bottom, left:right]
        
        # Resize to standard size
        if face_img.size > 0:
            face_img = cv2.resize(face_img, (224, 224))
            return face_img
        
        return None
    
    def extract_face_embedding(self, face_image: np.ndarray) -> Optional[np.ndarray]:
        """Extract 128-D face embedding using face_recognition."""
        try:
            import face_recognition
            # face_recognition expects RGB images
            face_encodings = face_recognition.face_encodings(face_image)
            
            if face_encodings:
                return face_encodings[0]  # Return first encoding (128-D vector)
            
            return None
        except Exception as e:
            logger.error(f"Error extracting face embedding: {e}")
            return None
    
    def process_media_for_enrollment(self, media_file, file_type: str) -> Dict:
        """Process video or image archive for facial enrollment."""
        results = {
            'frames_processed': 0,
            'faces_detected': 0,
            'embeddings': [],
            'face_images': [],
            'confidences': [],
            'errors': []
        }
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_type}') as tmp_file:
            for chunk in media_file.chunks():
                tmp_file.write(chunk)
            tmp_file_path = tmp_file.name
        
        try:
            # Extract frames/images
            if file_type in ['mp4', 'avi', 'mov']:
                frames = self.extract_frames_from_video(tmp_file_path)
            else:  # ZIP archive
                frames = self.extract_images_from_zip(tmp_file_path)
            
            results['frames_processed'] = len(frames)
            
            # Process each frame
            for i, frame in enumerate(frames):
                try:
                    # Detect faces
                    faces = self.detect_faces(frame)
                    
                    if not faces:
                        continue
                    
                    # Use the face with highest confidence
                    best_face = max(faces, key=lambda x: x['confidence'])
                    
                    # Align and crop face
                    face_img = self.align_and_crop_face(frame, best_face['box'])
                    
                    if face_img is not None:
                        # Extract embedding
                        embedding = self.extract_face_embedding(face_img)
                        
                        if embedding is not None:
                            results['embeddings'].append(embedding)
                            results['face_images'].append(face_img)
                            results['confidences'].append(best_face['confidence'])
                            results['faces_detected'] += 1
                
                except Exception as e:
                    results['errors'].append(f"Error processing frame {i}: {str(e)}")
                    logger.error(f"Error processing frame {i}: {e}")
            
        finally:
            # Clean up temporary file
            os.unlink(tmp_file_path)
        
        return results
    
    def calculate_average_embedding(self, embeddings: List[np.ndarray]) -> np.ndarray:
        """Calculate average embedding from multiple face embeddings."""
        if not embeddings:
            raise ValueError("No embeddings provided")
        
        # Convert to numpy array and calculate mean
        embeddings_array = np.array(embeddings)
        avg_embedding = np.mean(embeddings_array, axis=0)
        
        # Normalize the embedding
        norm = np.linalg.norm(avg_embedding)
        if norm > 0:
            avg_embedding = avg_embedding / norm
        
        return avg_embedding
    
    def create_thumbnail(self, face_images: List[np.ndarray], size: Tuple[int, int] = (150, 150)) -> ContentFile:
        """Create thumbnail from the best face image."""
        if not face_images:
            raise ValueError("No face images provided")
        
        # Use the middle image as it's likely to be of good quality
        best_image_idx = len(face_images) // 2
        best_image = face_images[best_image_idx]
        
        # Convert to PIL Image
        pil_image = Image.fromarray(best_image)
        
        # Resize to thumbnail size
        pil_image.thumbnail(size, Image.Resampling.LANCZOS)
        
        # Save to BytesIO
        thumb_io = io.BytesIO()
        pil_image.save(thumb_io, format='JPEG', quality=85)
        thumb_io.seek(0)
        
        # Create Django ContentFile
        return ContentFile(thumb_io.read(), name='thumbnail.jpg')
    
    def calculate_quality_metrics(self, results: Dict) -> Dict:
        """Calculate quality metrics for the enrollment."""
        metrics = {
            'face_detection_rate': 0.0,
            'average_confidence': 0.0,
            'embedding_consistency': 0.0,
            'overall_quality': 0.0
        }
        
        if results['frames_processed'] > 0:
            metrics['face_detection_rate'] = results['faces_detected'] / results['frames_processed']
        
        if results['confidences']:
            metrics['average_confidence'] = np.mean(results['confidences'])
        
        if len(results['embeddings']) > 1:
            # Calculate consistency as inverse of standard deviation
            embeddings_array = np.array(results['embeddings'])
            std_dev = np.mean(np.std(embeddings_array, axis=0))
            metrics['embedding_consistency'] = 1.0 - min(std_dev, 1.0)
        else:
            metrics['embedding_consistency'] = 1.0
        
        # Calculate overall quality score
        metrics['overall_quality'] = (
            metrics['face_detection_rate'] * 0.3 +
            metrics['average_confidence'] * 0.4 +
            metrics['embedding_consistency'] * 0.3
        )
        
        return metrics
