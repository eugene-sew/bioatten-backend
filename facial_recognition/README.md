# Facial Recognition Module

This module provides facial enrollment functionality for the BioAttend system, allowing administrators to enroll students' facial data for biometric authentication.

## Features

- **Video/Image Processing**: Accepts video files (MP4, AVI, MOV) or ZIP archives containing images
- **Face Detection**: Uses dlib/face_recognition for accurate face detection
- **Embedding Generation**: Creates 128-dimensional facial embeddings for authentication
- **Quality Metrics**: Provides detailed quality assessment of enrollments
- **Thumbnail Generation**: Automatically creates thumbnails for enrolled students
- **Enrollment History**: Tracks all enrollment attempts with success/failure status

## Installation

1. Install required packages:
```bash
pip install -r requirements.txt
```

2. Apply migrations:
```bash
python manage.py makemigrations facial_recognition
python manage.py migrate
```

## API Endpoints

- `POST /api/students/{id}/enroll/` - Enroll student facial data
- `GET /api/students/{id}/enroll/` - Check enrollment status
- `DELETE /api/students/{id}/enroll/` - Delete enrollment
- `GET /api/students/{id}/enrollment-attempts/` - View enrollment history
- `GET /api/enrollment-statistics/` - Get enrollment statistics

See [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) for detailed API documentation.

## Usage Example

```python
# Using the test script
python facial_recognition/test_enrollment.py

# Or using curl
curl -X POST http://localhost:8000/api/students/{student_id}/enroll/ \
  -H "Authorization: Bearer {token}" \
  -F "media=@/path/to/video.mp4"
```

## Technical Details

### Face Detection
- Primary: CNN model (GPU-accelerated)
- Fallback: HOG model (CPU-based)
- Confidence threshold: 0.95

### Quality Requirements
- Minimum faces detected: 5
- Maximum file sizes:
  - Video: 50MB
  - ZIP archive: 100MB

### Processing Workflow
1. Extract frames from video or images from ZIP
2. Detect faces in each frame
3. Align and crop detected faces
4. Generate 128-D embeddings
5. Average embeddings for robustness
6. Store embedding and generate thumbnail

## Model Architecture

### FacialEnrollment
- Stores facial embeddings and metadata
- One-to-one relationship with Student
- Binary field for 128-D embedding

### EnrollmentAttempt
- Tracks all enrollment attempts
- Records success/failure and processing metrics
- Useful for debugging and auditing

## Testing

Run the included test script:
```bash
python facial_recognition/test_enrollment.py
```

Update the script with:
- Admin credentials
- Valid student ID
- Path to test media file

## Troubleshooting

### Common Issues

1. **"No module named 'cv2'"**
   - Install OpenCV: `pip install opencv-python`

2. **"No faces detected"**
   - Ensure good lighting in video/images
   - Face should be clearly visible
   - Try different angles

3. **"dlib not found"**
   - Install cmake first: `brew install cmake` (macOS)
   - Then: `pip install dlib face_recognition`

### Performance Tips
- Use GPU for faster CNN face detection
- Process videos with good lighting
- Avoid excessive motion blur
- Optimal video length: 5-10 seconds
