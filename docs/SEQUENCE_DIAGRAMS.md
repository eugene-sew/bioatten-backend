# Sequence Diagrams

This document contains sequence diagrams for key user activities in the BioAttend system.

## 1. Student Attendance Clock-In

This diagram illustrates the process of a student clocking in for a scheduled class using facial recognition.

```mermaid
sequenceDiagram
    actor Student
    participant Frontend as React App
    participant Backend as Django API
    participant FaceRec as Face Verification Service
    participant DB as Database
    participant Pusher as Pusher Service

    Student->>+Frontend: Opens Attendance Clock-In/Out Page
    Frontend->>+Backend: GET /api/auth/users/me/ (get student profile)
    Backend->>+DB: Query authenticated user and student profile
    DB-->>-Backend: Return user with student_profile
    Backend-->>-Frontend: Return user data with group info
    
    Frontend->>+Backend: GET /api/schedules/today/?group={group_id}
    Backend->>+DB: Query today's schedules for student's group
    DB-->>-Backend: Return schedule list
    Backend-->>-Frontend: Return today's schedules
    
    Frontend->>+Backend: GET /api/attendance/status/{schedule_id}/ (for each schedule)
    Backend->>+DB: Query attendance log for student/schedule/date
    DB-->>-Backend: Return attendance status or none
    Backend-->>-Frontend: Return attendance status

    Student->>Frontend: Clicks "Clock In" for a schedule
    Frontend->>Student: Prompts for camera access
    Student->>Frontend: Grants camera access and takes photo
    Frontend->>Frontend: Captures single photo frame

    Frontend->>+Backend: POST /api/attendance/clock_in/ {snapshot, schedule_id}
    Backend->>Backend: Validate serializer and get authenticated student
    Backend->>+DB: Query schedule by ID
    DB-->>-Backend: Return schedule details
    
    Backend->>+FaceRec: verify_face(snapshot_base64, student_id)
    FaceRec->>+DB: Query FacialEnrollment for student
    DB-->>-FaceRec: Return stored face embedding
    FaceRec->>FaceRec: Decode base64 image and extract embedding
    FaceRec->>FaceRec: Compare embeddings using cosine similarity
    FaceRec-->>-Backend: Return {verified: bool, confidence: float, message: str}

    alt Face Verified Successfully
        Backend->>+DB: get_or_create AttendanceLog(student, schedule, date)
        DB-->>-Backend: Return attendance_log and created flag
        Backend->>Backend: Check if already clocked in
        Backend->>Backend: Determine if late (>10min after start_time)
        Backend->>+DB: Save attendance_log with status and check_in_time
        DB-->>-Backend: Confirm save
        Backend->>+FaceRec: save_verification_image(snapshot, attendance_log_id)
        FaceRec-->>-Backend: Return image_path
        Backend->>+DB: Update attendance_log.face_image_path
        DB-->>-Backend: Confirm update
        Backend->>+Pusher: trigger_faculty_notification(schedule_id, clock_in_data)
        Pusher-->>-Backend: Notification sent
        Backend-->>Frontend: {success: true, status: 'PRESENT'/'LATE', message, details}
        Frontend->>Student: Display 'Clock-in Successful'
    else Face Not Verified
        Backend-->>Frontend: {success: false, status: 'ABSENT', message, confidence}
        Frontend->>Student: Display error message with enrollment prompt
    end
    deactivate Backend

```

## 2. Student Facial Enrollment (Self-Enrollment)

This diagram shows the sequence for a student enrolling their own facial data through the biometric enrollment modal.

```mermaid
sequenceDiagram
    actor Student
    participant Frontend as React App
    participant Backend as Django API
    participant FaceProcessor as Face Processor Service
    participant DB as Database

    Student->>+Frontend: Opens Profile → Biometric Enrollment
    Frontend->>Frontend: Display BiometricEnrollmentModal
    Student->>Frontend: Clicks "Start Capture Process"
    Frontend->>Student: Prompts for camera access
    Student->>Frontend: Grants camera access
    
    loop Capture 5 Images
        Student->>Frontend: Positions face and clicks "Capture Next Image"
        Frontend->>Frontend: Capture photo via CameraCapture component
        Frontend->>Frontend: Store image as data URL
    end
    
    Student->>Frontend: Clicks "Process & Submit" (after 5 images captured)
    Frontend->>Frontend: Package images into ZIP using JSZip
    Frontend->>+Backend: POST /api/students/me/enroll/ {media: zip_file}
    
    Backend->>Backend: Validate authenticated user is student
    Backend->>+DB: CREATE EnrollmentAttempt(student, status='PROCESSING')
    DB-->>-Backend: Return attempt object
    
    Backend->>+FaceProcessor: process_media_for_enrollment(zip_file, 'zip')
    FaceProcessor->>FaceProcessor: Extract images from ZIP
    FaceProcessor->>FaceProcessor: Detect faces in each image
    FaceProcessor->>FaceProcessor: Extract face embeddings
    FaceProcessor-->>-Backend: Return {faces_detected, embeddings, face_images, errors}
    
    Backend->>Backend: Check if faces_detected >= 5
    
    alt Sufficient Faces Detected
        Backend->>+FaceProcessor: calculate_average_embedding(embeddings)
        FaceProcessor-->>-Backend: Return averaged embedding
        Backend->>+FaceProcessor: create_thumbnail(face_images)
        FaceProcessor-->>-Backend: Return thumbnail image
        Backend->>+FaceProcessor: calculate_quality_metrics(results)
        FaceProcessor-->>-Backend: Return quality metrics
        
        Backend->>+DB: update_or_create FacialEnrollment(student, embedding, quality_data)
        DB-->>-Backend: Return enrollment object and created flag
        Backend->>+DB: Save thumbnail image to enrollment.thumbnail
        DB-->>-Backend: Confirm thumbnail saved
        Backend->>+DB: Update EnrollmentAttempt(status='SUCCESS')
        DB-->>-Backend: Confirm attempt updated
        
        Backend-->>Frontend: {success: true, message: 'Successfully enrolled', enrollment_data}
        Frontend->>Student: Display 'Enrollment complete!' with success message
    else Insufficient Faces
        Backend->>+DB: Update EnrollmentAttempt(status='FAILED', error_message)
        DB-->>-Backend: Confirm attempt updated
        Backend-->>Frontend: {success: false, message: 'Insufficient faces detected'}
        Frontend->>Student: Display error message and retry option
    end
    deactivate Backend

```

## 3. Manual Clock-In Request

This diagram shows the sequence when a student requests manual clock-in and the lecturer receives a real-time notification to approve or dismiss the request.

```mermaid
sequenceDiagram
    actor Student
    actor Lecturer
    participant StudentFE as Student Frontend
    participant LecturerFE as Lecturer Frontend
    participant Backend as Django API
    participant DB as Database
    participant Pusher as Pusher Service

    Student->>+StudentFE: Opens Attendance Clock-In/Out Page
    StudentFE->>StudentFE: Display today's schedules with status
    Student->>StudentFE: Clicks hand-raised icon for manual request
    StudentFE->>Student: Prompt for reason (optional)
    Student->>StudentFE: Enters reason and confirms

    StudentFE->>+Backend: POST /api/attendance/manual_clock_in_request/ {schedule_id, reason}
    Backend->>Backend: Validate authenticated user is student
    Backend->>+DB: Query schedule and verify student enrollment
    DB-->>-Backend: Return schedule details
    Backend->>+DB: Check for existing attendance log (prevent duplicates)
    DB-->>-Backend: Return attendance status
    
    alt Student Not Already Clocked In
        Backend->>+Pusher: trigger_faculty_notification(schedule_id, manual_request_data)
        Note over Pusher: Channel: faculty-schedule-{schedule_id}<br/>Event: attendance-notification<br/>Data: {type: 'manual_clock_in_request', student_info, reason}
        Pusher-->>-Backend: Notification sent
        Backend-->>StudentFE: {success: true, message: 'Request sent to lecturer'}
        StudentFE->>Student: Display 'Manual clock-in request sent'
        
        Pusher->>+LecturerFE: Real-time notification on faculty-schedule-{schedule_id}
        LecturerFE->>LecturerFE: Detect manual_clock_in_request event
        LecturerFE->>Lecturer: Display interactive toast with student name, reason, and Approve/Dismiss buttons
        
        alt Lecturer Approves Request
            Lecturer->>LecturerFE: Clicks "Approve" button
            LecturerFE->>+Backend: POST /api/attendance/schedule/{schedule_id}/manual-clock-in/ {student_id}
            Backend->>+DB: CREATE/UPDATE AttendanceLog(student, schedule, date, is_manual_override=true)
            DB-->>-Backend: Return attendance_log
            Backend->>+Pusher: trigger_faculty_notification(schedule_id, manual_clock_in_data)
            Pusher-->>-Backend: Notification sent
            Backend-->>LecturerFE: {success: true, attendance: attendance_data}
            LecturerFE->>LecturerFE: Update attendance table and dismiss toast
            LecturerFE->>Lecturer: Display '{student_name} has been clocked in'
            deactivate Backend
        else Lecturer Dismisses Request
            Lecturer->>LecturerFE: Clicks "Dismiss" button
            LecturerFE->>LecturerFE: Dismiss toast notification
            Note over LecturerFE: No backend call needed for dismissal
        end
        deactivate LecturerFE
        
    else Student Already Clocked In
        Backend-->>StudentFE: {success: false, message: 'Already clocked in for today'}
        StudentFE->>Student: Display error message
    end
    deactivate Backend

```
