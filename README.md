# BioAttend Backend

Django REST API backend for the BioAttend facial recognition attendance system.

## Features

- PostgreSQL database configuration
- JWT authentication using djangorestframework-simplejwt
- CORS support for frontend integration
- Media file handling for facial recognition data
- Computer vision libraries: OpenCV, dlib, YOLOv8 (ultralytics)
- Five main apps: authentication, students, schedules, attendance, facial_recognition

## Setup Instructions

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Generate a secure 256-bit secret key:
   ```bash
   python generate_secret_key.py
   ```

3. Update the `.env` file with your database credentials and the generated secret key.

### 4. Database Setup

1. Create a PostgreSQL database:
   ```sql
   CREATE DATABASE bioattend_db;
   CREATE USER bioattend_user WITH PASSWORD 'your_secure_password';
   GRANT ALL PRIVILEGES ON DATABASE bioattend_db TO bioattend_user;
   ```

2. Run migrations:
   ```bash
   python manage.py migrate
   ```

### 5. Create Superuser

```bash
python manage.py createsuperuser
```

### 6. Collect Static Files (for production)

```bash
python manage.py collectstatic
```

### 7. Run Development Server

```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000/`

## Project Structure

- `authentication/` - User authentication and JWT token management
- `students/` - Student profile and enrollment management
- `schedules/` - Class schedules and timetables
- `attendance/` - Attendance records and reporting
- `facial_recognition/` - Face detection, encoding, and matching

## Key Dependencies

- **Django 5.1.7** - Web framework
- **PostgreSQL** - Database (via psycopg2-binary 2.9.11)
- **Django REST Framework 3.15.2** - REST API toolkit
- **djangorestframework-simplejwt 5.3.1** - JWT authentication
- **OpenCV 4.10.0.85** - Computer vision
- **dlib 19.24.6** - Face recognition
- **ultralytics 8.3.64** - YOLOv8 for object detection
- **Pillow 11.0.0** - Image processing
- **numpy 1.26.4** - Numerical computing

## Security Notes

- Never commit the `.env` file to version control
- Always use HTTPS in production
- Regularly update dependencies for security patches
- Configure proper CORS origins for production
