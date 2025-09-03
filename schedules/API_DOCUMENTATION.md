# Schedule Management API Documentation

## Base URL
`/api/schedules/`

## Endpoints

### 1. List Schedules
**GET** `/api/schedules/`

Get a paginated list of schedules with optional filtering.

#### Query Parameters:
- `date_from` (string, YYYY-MM-DD): Filter schedules from this date
- `date_to` (string, YYYY-MM-DD): Filter schedules up to this date
- `date` (string, YYYY-MM-DD): Filter schedules for a specific date
- `group` (integer): Filter by student group ID
- `faculty` (integer): Filter by faculty ID
- `course_code` (string): Filter by course code (partial match)
- `search` (string): Search in title, course_code, room, description
- `ordering` (string): Order results by field (e.g., `date`, `-date`, `start_time`)
- `page` (integer): Page number for pagination
- `page_size` (integer): Number of items per page (max: 100)

#### Response:
```json
{
  "count": 50,
  "next": "http://api/schedules/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "title": "Introduction to Biology",
      "course_code": "BIO101",
      "date": "2024-01-15",
      "start_time": "09:00:00",
      "end_time": "10:30:00",
      "assigned_group_name": "Biology Year 1 - Section A",
      "faculty_name": "Dr. John Smith",
      "room": "Lab 201"
    }
  ]
}
```

### 2. Create Schedule
**POST** `/api/schedules/`

Create a new schedule entry.

#### Request Body:
```json
{
  "title": "Introduction to Biology",
  "course_code": "BIO101",
  "date": "2024-01-15",
  "start_time": "09:00:00",
  "end_time": "10:30:00",
  "clock_in_opens_at": "08:45:00",
  "clock_in_closes_at": "09:15:00",
  "assigned_group": 1,
  "faculty": 1,
  "room": "Lab 201",
  "description": "First lecture of the semester"
}
```

#### Validation Rules:
- `end_time` must be after `start_time`
- `clock_in_opens_at` cannot be after class start time
- `clock_in_closes_at` cannot be before class start time
- `clock_in_opens_at` must be before `clock_in_closes_at`
- Clock-in window cannot open more than 1 hour before class
- Clock-in window cannot close more than 1 hour after class starts
- No double-booking for same group/faculty at same date and time

### 3. Get Schedule Details
**GET** `/api/schedules/{id}/`

Get detailed information about a specific schedule.

#### Response:
```json
{
  "id": 1,
  "title": "Introduction to Biology",
  "course_code": "BIO101",
  "date": "2024-01-15",
  "start_time": "09:00:00",
  "end_time": "10:30:00",
  "clock_in_opens_at": "08:45:00",
  "clock_in_closes_at": "09:15:00",
  "assigned_group": 1,
  "assigned_group_detail": {
    "id": 1,
    "name": "Biology Year 1 - Section A",
    "code": "BIO1A"
  },
  "faculty": 1,
  "faculty_detail": {
    "id": 1,
    "faculty_id": "FAC001",
    "name": "Dr. John Smith",
    "department": "Biology"
  },
  "room": "Lab 201",
  "description": "First lecture of the semester",
  "created_at": "2024-01-10T10:00:00Z",
  "updated_at": "2024-01-10T10:00:00Z"
}
```

### 4. Update Schedule
**PUT** `/api/schedules/{id}/`
**PATCH** `/api/schedules/{id}/`

Update an existing schedule. PUT requires all fields, PATCH allows partial updates.

### 5. Delete Schedule
**DELETE** `/api/schedules/{id}/`

Soft delete a schedule (marks as deleted but retains in database).

### 6. Today's Schedules
**GET** `/api/schedules/today/`

Get all schedules for the current date.

### 7. Upcoming Schedules
**GET** `/api/schedules/upcoming/`

Get schedules for the next 7 days (paginated).

### 8. Schedules by Group
**GET** `/api/schedules/by_group/?group_id={id}`

Get all schedules for a specific student group.

### 9. Schedules by Faculty
**GET** `/api/schedules/by_faculty/?faculty_id={id}`

Get all schedules for a specific faculty member.

## Error Responses

### Validation Error (400)
```json
{
  "end_time": ["End time must be after start time."],
  "clock_in_opens_at": ["Clock-in cannot open after the class starts."]
}
```

### Not Found (404)
```json
{
  "detail": "Not found."
}
```

### Unauthorized (401)
```json
{
  "detail": "Authentication credentials were not provided."
}
```

## Examples

### Filter schedules for next week
```
GET /api/schedules/?date_from=2024-01-15&date_to=2024-01-21
```

### Search for a specific course
```
GET /api/schedules/?course_code=BIO101&ordering=-date
```

### Get schedules for a specific group on a specific date
```
GET /api/schedules/?group=1&date=2024-01-15
```
