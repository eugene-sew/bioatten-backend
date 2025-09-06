# BioAttend Merged User Workflow

This flowchart provides a unified view of how the Student, Faculty, and Admin workflows interconnect within the BioAttend system, highlighting key points of interaction.

## Unified Workflow Diagram

```mermaid
graph TD
    subgraph "Admin Setup"
        A1[Admin Logs In] --> A2[Manages Courses, Schedules, & Groups]
        A2 --> A3[Assigns Faculty to Schedule]
        A2 --> A4[Assigns Student to Group]
    end

    subgraph "Student Actions"
        S1[Student Logs In] --> S2[Views Assigned Schedules]
        S2 --> S3{Clock-In/Out}
        S3 -- Facial Recognition --> S4[Attendance Logged]
        S3 -- Manual Request --> S5[Request Sent]
    end

    subgraph "Faculty Actions"
        F1[Faculty Logs In] --> F2[Views Assigned Schedules]
        F2 --> F3[Monitors Real-time Attendance]
        F3 --> F4[Manually Adjusts Attendance]
    end
    
    subgraph "System & Data"
        D1[Attendance Database]
        D2[Pusher Service]
    end

    %% Interconnections
    A3 -- Enables Access --> F2
    A4 -- Enables Access --> S2
    
    S4 -- Writes to --> D1
    S5 -- Triggers --> D2
    
    D2 -- Real-time Notification --> F3
    F3 -- Reads from --> D1
    F4 -- Writes to --> D1

    subgraph "Reporting"
        R1[Admin Views System-wide Reports]
        R2[Faculty Views Schedule Reports]
    end
    
    D1 -- Provides Data --> R1
    D1 -- Provides Data --> R2

    %% Styling
    classDef admin fill:#f96,stroke:#333,stroke-width:2px;
    classDef student fill:#c9d,stroke:#333,stroke-width:2px;
    classDef faculty fill:#9cf,stroke:#333,stroke-width:2px;
    classDef system fill:#9c9,stroke:#333,stroke-width:2px;

    class A1,A2,A3,A4,R1 admin;
    class S1,S2,S3,S4,S5 student;
    class F1,F2,F3,F4,R2 faculty;
    class D1,D2 system;
```

### Workflow Explanation

1.  **Setup (Admin)**: The Admin is responsible for the initial setup, including creating courses, schedules, and student groups. They assign faculty to schedules and students to groups, which grants them access to the relevant parts of the system.
2.  **Attendance (Student)**: The Student logs in and can only see the schedules they are assigned to. They can then clock in or out using facial recognition or request a manual clock-in.
3.  **Monitoring (Faculty)**: The Faculty member logs in to view the schedules they are assigned to. They can monitor attendance in real-time. When a student sends a manual clock-in request, the faculty receives a real-time notification to approve or dismiss it.
4.  **Data Flow**: All attendance events are recorded in the central **Attendance Database**. Real-time events are pushed through the **Pusher Service**.
5.  **Reporting**: Both Admins and Faculty can view attendance reports. Admins have access to system-wide data, while Faculty can view reports for the specific schedules they manage.
