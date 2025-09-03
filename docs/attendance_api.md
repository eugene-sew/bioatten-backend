# Attendance API Documentation

## Overview
The Attendance API provides endpoints for students to clock in and clock out of classes using facial recognition verification. It also includes real-time update capabilities via WebSockets or Server-Sent Events (SSE).

## Authentication
All endpoints require JWT authentication. Include the access token in the Authorization header:
```
Authorization: Bearer <access_token>
```

## Endpoints

### 1. Clock In
**POST** `/api/attendance/clock_in/`

Records a student's attendance by verifying their face against their enrolled facial data.

#### Request Body
```json
{
    "snapshot": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
    "schedule_id": 1
}
```

#### Response (Success - 201 Created)
```json
{
    "success": true,
    "status": "PRESENT",
    "message": "Successfully clocked in at 09:05:23",
    "student_name": "John Doe",
    "course_code": "CS101",
    "check_in_time": "09:05:23",
    "confidence_score": 0.85,
    "is_late": false,
    "attendance_log_id": 123
}
```

#### Response (Late Arrival - 200 OK)
```json
{
    "success": true,
    "status": "LATE",
    "message": "Successfully clocked in at 09:15:23",
    "student_name": "John Doe",
    "course_code": "CS101",
    "check_in_time": "09:15:23",
    "confidence_score": 0.85,
    "is_late": true,
    "attendance_log_id": 124
}
```

#### Response (Face Verification Failed - 401 Unauthorized)
```json
{
    "success": false,
    "status": "ABSENT",
    "message": "Face similarity (0.45) below threshold (0.6)",
    "confidence_score": 0.45
}
```

#### Response (No Enrollment - 401 Unauthorized)
```json
{
    "success": false,
    "status": "ABSENT",
    "message": "Student has no active facial enrollment",
    "confidence_score": 0.0
}
```

### 2. Clock Out
**POST** `/api/attendance/clock_out/`

Records when a student leaves the class, with face verification.

#### Request Body
```json
{
    "snapshot": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
    "schedule_id": 1
}
```

#### Response (Success - 200 OK)
```json
{
    "success": true,
    "status": "PRESENT",
    "message": "Successfully clocked out at 10:50:15",
    "student_name": "John Doe",
    "course_code": "CS101",
    "check_in_time": "09:05:23",
    "check_out_time": "10:50:15",
    "confidence_score": 0.87,
    "attendance_log_id": 123
}
```

#### Response (Not Clocked In - 400 Bad Request)
```json
{
    "success": false,
    "message": "Cannot clock out without clocking in first"
}
```

### 3. Attendance Status
**GET** `/api/attendance/status/{schedule_id}/`

Get the current attendance status for a student in a specific schedule.

#### Response (Has Attendance - 200 OK)
```json
{
    "success": true,
    "has_attendance": true,
    "attendance": {
        "id": 123,
        "student": 5,
        "student_name": "John Doe",
        "student_id": "STU001",
        "schedule": 1,
        "course_code": "CS101",
        "course_name": "Introduction to Computer Science",
        "date": "2024-01-15",
        "status": "PRESENT",
        "check_in_time": "09:05:23",
        "check_out_time": "10:50:15",
        "face_recognition_confidence": 0.85,
        "is_late": false,
        "is_manual_override": false,
        "override_reason": "",
        "created_at": "2024-01-15T09:05:23Z"
    }
}
```

#### Response (No Attendance - 200 OK)
```json
{
    "success": true,
    "has_attendance": false,
    "message": "No attendance record for today"
}
```

## Real-Time Updates

### WebSocket Connection
**WS** `ws://localhost:8000/ws/attendance/updates/{schedule_id}/`

Connect to receive real-time attendance updates for a specific schedule.

#### Connection Flow
1. Connect with JWT token in headers or query params
2. Receive connection confirmation:
```json
{
    "type": "connection_established",
    "message": "Connected to attendance updates for schedule 1"
}
```

3. Receive attendance updates:
```json
{
    "type": "attendance_update",
    "data": {
        "type": "clock_in",
        "attendance_log": {
            "id": 125,
            "student_name": "Jane Smith",
            "status": "PRESENT",
            "check_in_time": "09:07:45"
        },
        "timestamp": "2024-01-15T09:07:45Z"
    }
}
```

### Server-Sent Events (Alternative)
**GET** `/api/attendance/updates/sse/{schedule_id}/`

Stream real-time attendance updates using SSE.

#### Response Stream
```
data: {"type": "connected", "schedule_id": 1}

data: {"type": "clock_in", "attendance_log": {...}, "timestamp": "2024-01-15T09:07:45Z"}

: heartbeat

data: {"type": "clock_out", "attendance_log": {...}, "timestamp": "2024-01-15T10:52:30Z"}
```

## Face Verification Process

The face verification pipeline works as follows:

1. **Face Detection**: Detect faces in the uploaded snapshot
2. **Face Extraction**: Extract and align the detected face
3. **Embedding Generation**: Generate a 128-dimensional face embedding
4. **Similarity Calculation**: Compare with stored enrollment embedding using cosine similarity
5. **Threshold Check**: Verify similarity is above 0.6 (60% match)

## Status Codes

- `201 Created` - Successful clock-in (new record)
- `200 OK` - Successful operation
- `400 Bad Request` - Invalid input or business logic error
- `401 Unauthorized` - Authentication or face verification failed
- `403 Forbidden` - User doesn't have permission
- `404 Not Found` - Resource not found

## Error Handling

All error responses follow this format:
```json
{
    "success": false,
    "message": "Error description",
    "errors": {
        "field_name": ["Specific error message"]
    }
}
```

## Best Practices

1. **Image Quality**: Ensure snapshots are well-lit with clear face visibility
2. **Single Face**: Only one face should be present in the snapshot
3. **Face Position**: Face should be centered and front-facing
4. **Resolution**: Minimum 224x224 pixels for best results
5. **Format**: JPEG or PNG images encoded as base64 data URLs

## Rate Limiting

- Clock-in/Clock-out: 10 requests per minute per user
- Status checks: 60 requests per minute per user
- WebSocket connections: 1 per user per schedule
