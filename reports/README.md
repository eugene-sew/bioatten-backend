# Reports & Analytics Module API Documentation

## Overview
The Reports & Analytics module provides comprehensive attendance reporting and data visualization endpoints for the BioAttend system.

## Endpoints

### 1. Attendance Report
**URL:** `/api/reports/attendance/`  
**Method:** `GET`  
**Authentication:** Required (JWT Token)

#### Query Parameters:
- `group` (required): Student group code
- `from` (required): Start date (YYYY-MM-DD)
- `to` (required): End date (YYYY-MM-DD)
- `format` (optional): Output format - `json` (default), `csv`, or `excel`

#### Example Request:
```bash
GET /api/reports/attendance/?group=CS101&from=2024-01-01&to=2024-01-31&format=json
```

#### Response Structure (JSON):
```json
{
  "report_period": {
    "from": "2024-01-01",
    "to": "2024-01-31",
    "group": {
      "code": "CS101",
      "name": "Computer Science 101",
      "total_students": 30
    }
  },
  "overall_statistics": {
    "total_classes": 20,
    "total_attendance_records": 600,
    "average_attendance_rate": 85.5
  },
  "daily_attendance": [
    {
      "date": "2024-01-01",
      "total_students": 30,
      "present_count": 25,
      "absent_count": 3,
      "late_count": 2,
      "excused_count": 0,
      "attendance_percentage": 90.0
    }
  ],
  "most_absent_students": [
    {
      "student_id": "STU001",
      "first_name": "John",
      "last_name": "Doe",
      "email": "john.doe@example.com",
      "absence_count": 5
    }
  ],
  "punctuality_distribution": [
    {
      "status": "PRESENT",
      "count": 450
    },
    {
      "status": "ABSENT",
      "count": 80
    },
    {
      "status": "LATE",
      "count": 50
    },
    {
      "status": "EXCUSED",
      "count": 20
    }
  ]
}
```

### 2. Chart Data
**URL:** `/api/reports/charts/`  
**Method:** `GET`  
**Authentication:** Required (JWT Token)

#### Query Parameters:
- `type` (required): Chart type - `daily`, `status`, `weekly`, or `punctuality`
- `group` (required): Student group code
- `from` (required): Start date (YYYY-MM-DD)
- `to` (required): End date (YYYY-MM-DD)

#### Chart Types:

##### Daily Attendance Trend (type=daily)
Returns data for a line chart showing daily attendance percentage trends.

```json
{
  "chart_type": "line",
  "title": "Daily Attendance Percentage",
  "data": {
    "labels": ["2024-01-01", "2024-01-02", "2024-01-03"],
    "datasets": [{
      "label": "Attendance %",
      "data": [90.0, 85.5, 92.3],
      "borderColor": "rgb(75, 192, 192)",
      "backgroundColor": "rgba(75, 192, 192, 0.2)"
    }]
  }
}
```

##### Status Distribution (type=status)
Returns data for a pie chart showing attendance status distribution.

```json
{
  "chart_type": "pie",
  "title": "Attendance Status Distribution",
  "data": {
    "labels": ["PRESENT", "ABSENT", "LATE", "EXCUSED"],
    "datasets": [{
      "data": [450, 80, 50, 20],
      "backgroundColor": [
        "rgb(75, 192, 192)",
        "rgb(255, 99, 132)",
        "rgb(255, 205, 86)",
        "rgb(54, 162, 235)"
      ]
    }]
  }
}
```

##### Weekly Summary (type=weekly)
Returns data for a bar chart showing weekly attendance breakdown.

```json
{
  "chart_type": "bar",
  "title": "Weekly Attendance Summary",
  "data": {
    "labels": ["Week of 2024-01-01", "Week of 2024-01-08"],
    "datasets": [
      {
        "label": "Present",
        "data": [125, 130],
        "backgroundColor": "rgb(75, 192, 192)"
      },
      {
        "label": "Absent",
        "data": [20, 15],
        "backgroundColor": "rgb(255, 99, 132)"
      },
      {
        "label": "Late",
        "data": [10, 12],
        "backgroundColor": "rgb(255, 205, 86)"
      }
    ]
  }
}
```

##### Punctuality Analysis (type=punctuality)
Returns data for a line chart showing average minutes late/early over time.

```json
{
  "chart_type": "line",
  "title": "Average Punctuality (Minutes from Class Start)",
  "data": {
    "labels": ["2024-01-01", "2024-01-02", "2024-01-03"],
    "datasets": [{
      "label": "Minutes Late (+) / Early (-)",
      "data": [2.5, -1.2, 3.8],
      "borderColor": "rgb(153, 102, 255)",
      "backgroundColor": "rgba(153, 102, 255, 0.2)",
      "tension": 0.1
    }]
  }
}
```

### 3. Individual Student Report
**URL:** `/api/reports/student/{student_id}/`  
**Method:** `GET`  
**Authentication:** Required (JWT Token)

#### Path Parameters:
- `student_id`: Student ID

#### Query Parameters:
- `from` (optional): Start date (YYYY-MM-DD) - defaults to current semester start
- `to` (optional): End date (YYYY-MM-DD) - defaults to today

#### Example Request:
```bash
GET /api/reports/student/STU001/?from=2024-01-01&to=2024-01-31
```

#### Response Structure:
```json
{
  "student": {
    "id": "STU001",
    "name": "John Doe",
    "email": "john.doe@example.com",
    "group": {
      "code": "CS101",
      "name": "Computer Science 101"
    }
  },
  "report_period": {
    "from": "2024-01-01",
    "to": "2024-01-31"
  },
  "statistics": {
    "total_classes": 20,
    "present": 15,
    "absent": 3,
    "late": 2,
    "excused": 0,
    "attendance_rate": 85.0
  },
  "attendance_records": [
    {
      "date": "2024-01-01",
      "course_code": "CS101",
      "course_title": "Introduction to Programming",
      "scheduled_time": "09:00 - 10:30",
      "status": "PRESENT",
      "check_in_time": "08:55",
      "check_out_time": "10:25",
      "is_late": false,
      "is_manual_override": false
    }
  ]
}
```

## File Export Formats

### CSV Export
When `format=csv` is specified, the attendance report is returned as a CSV file with the following structure:
- Header section with report metadata
- Daily attendance statistics
- Most absent students list

### Excel Export
When `format=excel` is specified, the attendance report is returned as an Excel file with multiple sheets:
1. **Overview**: Summary statistics and metadata
2. **Daily Attendance**: Day-by-day attendance breakdown
3. **Most Absent Students**: Top 10 students with most absences
4. **Punctuality Distribution**: Status count breakdown

## Error Responses

All endpoints return appropriate HTTP status codes:
- `200 OK`: Successful request
- `400 Bad Request`: Missing or invalid parameters
- `401 Unauthorized`: Missing or invalid authentication
- `404 Not Found`: Resource not found (e.g., invalid group code or student ID)

Error response format:
```json
{
  "error": "Error message describing the issue"
}
```

## Usage Examples

### Python (using requests)
```python
import requests

headers = {
    'Authorization': 'Bearer YOUR_JWT_TOKEN'
}

# Get attendance report
response = requests.get(
    'http://localhost:8000/api/reports/attendance/',
    params={
        'group': 'CS101',
        'from': '2024-01-01',
        'to': '2024-01-31',
        'format': 'json'
    },
    headers=headers
)

data = response.json()
```

### JavaScript (using fetch)
```javascript
const token = 'YOUR_JWT_TOKEN';

// Get chart data
fetch('http://localhost:8000/api/reports/charts/?type=daily&group=CS101&from=2024-01-01&to=2024-01-31', {
    headers: {
        'Authorization': `Bearer ${token}`
    }
})
.then(response => response.json())
.then(data => {
    // Use data for Chart.js or other visualization library
    console.log(data);
});
```

## Integration with Frontend

The chart data endpoints are designed to work seamlessly with popular charting libraries:
- **Chart.js**: Data structure matches Chart.js dataset format
- **D3.js**: JSON data can be easily transformed for D3 visualizations
- **Recharts**: Compatible with React-based charting library

## Performance Considerations

1. **Date Range**: Limit date ranges to reasonable periods (e.g., max 1 year) to ensure good performance
2. **Caching**: Consider implementing caching for frequently requested reports
3. **Pagination**: For large datasets, consider implementing pagination in future versions
4. **Database Indexes**: Ensure proper indexes on date and foreign key fields for optimal query performance
