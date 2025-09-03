# Attendance Clock-In/Clock-Out System

## Overview
This module implements a facial recognition-based attendance system that allows students to clock in and clock out of classes. The system verifies student identity through face recognition and provides real-time updates to administrators.

## Features

### Core Functionality
- **Face Verification**: Uses cosine similarity comparison against enrolled facial embeddings
- **Clock-In/Clock-Out**: Records attendance with timestamps
- **Late Detection**: Automatically marks students as late (>10 minutes after class start)
- **Real-Time Updates**: Broadcasts attendance updates via WebSocket or SSE
- **Audit Trail**: Saves snapshots for verification history

### API Endpoints
1. **POST `/api/attendance/clock_in/`** - Clock in with face verification
2. **POST `/api/attendance/clock_out/`** - Clock out with face verification
3. **GET `/api/attendance/status/{schedule_id}/`** - Get current attendance status
4. **WS `/ws/attendance/updates/{schedule_id}/`** - WebSocket for real-time updates
5. **GET `/api/attendance/updates/sse/{schedule_id}/`** - SSE for real-time updates

## Technical Implementation

### Face Verification Pipeline
```
1. Receive base64 encoded snapshot
2. Decode and process image
3. Detect faces using face_recognition (dlib)
4. Extract 128-D face embedding
5. Compare with stored enrollment embedding
6. Verify similarity > 0.6 threshold
7. Create/update attendance record
```

### Models
- **AttendanceLog**: Stores attendance records with timestamps and verification data
- **FaceVerificationService**: Handles face detection and verification logic

### Real-Time Updates
The system supports two methods for real-time updates:
1. **WebSockets** (via Django Channels) - Full duplex communication
2. **Server-Sent Events (SSE)** - Simpler one-way updates

## Installation

1. Install required packages:
```bash
pip install -r requirements_attendance.txt
```

2. Install Redis for WebSocket support:
```bash
# macOS
brew install redis

# Ubuntu/Debian
sudo apt-get install redis-server
```

3. Run migrations:
```bash
python manage.py migrate attendance
```

## Configuration

Add to your `.env` file:
```env
# Face verification settings
FACE_VERIFICATION_THRESHOLD=0.6
LATE_THRESHOLD_MINUTES=10

# Redis configuration for WebSockets
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
```

## Usage Example

### Clock-In Request
```python
import requests
import base64

# Prepare snapshot
with open('student_photo.jpg', 'rb') as f:
    image_base64 = base64.b64encode(f.read()).decode('utf-8')

# Make request
response = requests.post(
    'http://localhost:8000/api/attendance/clock_in/',
    json={
        'snapshot': f'data:image/jpeg;base64,{image_base64}',
        'schedule_id': 1
    },
    headers={'Authorization': 'Bearer <token>'}
)

print(response.json())
```

### WebSocket Connection (JavaScript)
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/attendance/updates/1/');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'attendance_update') {
        console.log('New attendance update:', data.data);
    }
};
```

### SSE Connection (JavaScript)
```javascript
const eventSource = new EventSource(
    'http://localhost:8000/api/attendance/updates/sse/1/',
    { headers: { 'Authorization': 'Bearer <token>' } }
);

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Attendance update:', data);
};
```

## Testing

Run the test script:
```bash
python test_attendance_api.py
```

This will test:
- Clock-in functionality
- Clock-out functionality
- Attendance status retrieval
- Face verification responses

## Security Considerations

1. **Face Verification**: 0.6 cosine similarity threshold prevents unauthorized access
2. **Authentication**: All endpoints require JWT authentication
3. **Permission Checks**: Students can only access their own attendance
4. **Audit Trail**: All clock-in/out images are saved for verification
5. **Rate Limiting**: Prevents abuse of the API endpoints

## Performance Considerations

1. **Face Processing**: Face detection/embedding extraction takes ~200-500ms
2. **WebSocket Scaling**: Use Redis for multi-server deployments
3. **Image Storage**: Clock-in/out images are compressed to save space
4. **Database Indexing**: Attendance logs indexed by date and schedule

## Troubleshooting

### Common Issues

1. **"No face detected in snapshot"**
   - Ensure good lighting and clear face visibility
   - Face should be centered in the image

2. **"Face similarity below threshold"**
   - Re-enroll with better quality images
   - Ensure consistent lighting conditions

3. **WebSocket connection fails**
   - Check Redis is running
   - Verify ASGI server is used (not WSGI)

4. **SSE connection drops**
   - Check nginx/proxy buffering settings
   - Ensure proper CORS configuration

## Future Enhancements

1. **Anti-Spoofing**: Implement liveness detection
2. **Multiple Faces**: Support group attendance
3. **Offline Mode**: Queue attendance for sync
4. **Analytics**: Attendance patterns and insights
5. **Mobile SDK**: Native mobile integration
