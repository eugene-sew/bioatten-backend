# Facial Recognition API Documentation

## Overview

The Facial Recognition module provides endpoints for enrolling students' facial data and managing facial enrollments. It processes video files or image archives to extract facial embeddings for biometric authentication.

## Endpoints

### 1. Enroll Student Facial Data

**Endpoint:** `POST /api/students/{student_id}/enroll/`

**Description:** Process video or image archive to enroll a student's facial data.

**Authentication:** Required (Admin only)

**Parameters:**
- `student_id` (path parameter): The ID of the student to enroll

**Request Body:** Multipart form data
- `media` (file): Video file (MP4, AVI, MOV) or ZIP archive containing images

**Response:**
```json
{
  "success": true,
  "message": "Successfully enrolled facial data for John Doe",
  "enrollment": {
    "id": "uuid",
    "student": "student_id",
    "student_name": "John Doe",
    "student_id": "STU001",
    "thumbnail": "/media/facial_thumbnails/student_123_thumbnail.jpg",
    "face_confidence": 0.95,
    "embedding_quality": 0.87,
    "num_faces_detected": 25,
    "enrollment_date": "2024-01-15T10:30:00Z",
    "last_updated": "2024-01-15T10:30:00Z",
    "is_active": true,
    "embedding_base64": null  // Only included if ?include_embedding=true
  },
  "quality_metrics": {
    "face_detection_rate": 0.83,
    "average_confidence": 0.95,
    "embedding_consistency": 0.92,
    "overall_quality": 0.87
  }
}
```

**Error Responses:**
- `400 Bad Request`: Invalid input data or insufficient faces detected
- `404 Not Found`: Student not found
- `500 Internal Server Error`: Processing error

### 2. Get Student Enrollment Status

**Endpoint:** `GET /api/students/{student_id}/enroll/`

**Description:** Check if a student has been enrolled and get enrollment details.

**Authentication:** Required (Admin only)

**Parameters:**
- `student_id` (path parameter): The ID of the student
- `include_embedding` (query parameter, optional): Include base64 encoded embedding in response

**Response (Enrolled):**
```json
{
  "success": true,
  "enrolled": true,
  "enrollment": {
    "id": "uuid",
    "student": "student_id",
    "student_name": "John Doe",
    "student_id": "STU001",
    "thumbnail": "/media/facial_thumbnails/student_123_thumbnail.jpg",
    "face_confidence": 0.95,
    "embedding_quality": 0.87,
    "num_faces_detected": 25,
    "enrollment_date": "2024-01-15T10:30:00Z",
    "last_updated": "2024-01-15T10:30:00Z",
    "is_active": true
  }
}
```

**Response (Not Enrolled):**
```json
{
  "success": true,
  "enrolled": false,
  "message": "Student has not been enrolled yet"
}
```

### 3. Delete Student Enrollment

**Endpoint:** `DELETE /api/students/{student_id}/enroll/`

**Description:** Delete a student's facial enrollment data.

**Authentication:** Required (Admin only)

**Parameters:**
- `student_id` (path parameter): The ID of the student

**Response:**
```json
{
  "success": true,
  "message": "Successfully deleted facial enrollment for John Doe"
}
```

### 4. Get Enrollment Attempts

**Endpoint:** `GET /api/students/{student_id}/enrollment-attempts/`

**Description:** Get history of enrollment attempts for a student.

**Authentication:** Required (Admin only)

**Parameters:**
- `student_id` (path parameter): The ID of the student

**Response:**
```json
{
  "success": true,
  "attempts": [
    {
      "id": "uuid",
      "student": "student_id",
      "student_name": "John Doe",
      "status": "SUCCESS",
      "frames_processed": 30,
      "faces_detected": 25,
      "error_message": null,
      "processing_time": 12.5,
      "created_at": "2024-01-15T10:30:00Z"
    },
    {
      "id": "uuid",
      "student": "student_id",
      "student_name": "John Doe",
      "status": "FAILED",
      "frames_processed": 30,
      "faces_detected": 3,
      "error_message": "Insufficient faces detected: 3. Minimum 5 required.",
      "processing_time": 8.2,
      "created_at": "2024-01-15T10:15:00Z"
    }
  ]
}
```

### 5. Get Enrollment Statistics

**Endpoint:** `GET /api/enrollment-statistics/`

**Description:** Get overall enrollment statistics.

**Authentication:** Required (Admin only)

**Response:**
```json
{
  "total_students": 150,
  "enrolled_students": 125,
  "enrollment_rate": 0.833,
  "average_quality": 0.89,
  "recent_enrollments": [
    {
      "id": "uuid",
      "student_name": "John Doe",
      "student_id": "STU001",
      "enrollment_date": "2024-01-15T10:30:00Z",
      "embedding_quality": 0.87
    }
  ],
  "failed_attempts_today": 3
}
```

## Technical Details

### Face Detection
- Uses `face_recognition` library (dlib) for face detection
- Supports both CNN (GPU) and HOG (CPU) models
- Automatically falls back to HOG if CNN fails

### Embedding Extraction
- Generates 128-dimensional face embeddings
- Uses `face_recognition` library's deep learning model
- Embeddings are averaged across multiple detected faces for robustness

### Quality Metrics
- **Face Detection Rate**: Percentage of frames where faces were detected
- **Average Confidence**: Mean confidence score of face detections
- **Embedding Consistency**: Measure of similarity between multiple embeddings
- **Overall Quality**: Weighted combination of all metrics

### Storage
- Embeddings stored as binary (pickle) in database
- Thumbnails stored in media directory
- Support for base64 encoding of embeddings for API responses

### Requirements
- Minimum 5 faces must be detected for successful enrollment
- Supports video files: MP4, AVI, MOV (max 50MB)
- Supports image archives: ZIP (max 100MB)
- Images in archives: JPG, JPEG, PNG, BMP

## Error Handling

The API provides detailed error messages for common issues:
- Invalid file formats
- File size limits exceeded
- Insufficient faces detected
- Processing errors
- Student not found

All errors include appropriate HTTP status codes and descriptive messages to help with troubleshooting.
