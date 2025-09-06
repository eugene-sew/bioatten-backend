# BioAttend Moderately Detailed Workflow

This flowchart provides a balanced overview of the user workflows, adding key actions for each role to show how they interact with the BioAttend system without excessive detail.

## Moderately Detailed Workflow Diagram

```mermaid
graph TD
    subgraph "User Roles & Key Actions"
        direction LR
        subgraph Admin
            A[Admin] --> A1["Manage Users, Courses, & Schedules"]
        end
        subgraph Faculty
            F[Faculty] --> F1["Monitor Real-time Attendance"]
            F1 --> F2["Handle Manual Clock-In Requests"]
        end
        subgraph Student
            S[Student] --> S1["Clock-In/Out via Facial Recognition"]
            S1 --> S2["Manage Biometric Profile"]
        end
    end

    subgraph "System Components"
        SYS[BioAttend System]
        DB[(Database)]
        RT[Real-time Service]
    end

    %% Connections
    A1 -- Configures --> SYS
    S1 -- Sends Attendance Data --> SYS
    F1 -- Views Data From --> SYS
    F2 -- Responds to --> RT
    S1 -- Triggers --> RT

    SYS -- Reads/Writes --> DB
    SYS -- Pushes to --> RT
    RT -- Updates --> F1

    %% Styling
    classDef admin fill:#f96,stroke:#333,stroke-width:2px;
    classDef faculty fill:#9cf,stroke:#333,stroke-width:2px;
    classDef student fill:#c9d,stroke:#333,stroke-width:2px;
    classDef system fill:#9c9,stroke:#333,stroke-width:2px;

    class A,A1 admin;
    class F,F1,F2 faculty;
    class S,S1,S2 student;
    class SYS,DB,RT system;
```

### Key Interaction Points

-   **Admin**: Primarily responsible for the initial setup and ongoing management of the system's core data (users, courses, schedules).
-   **Student**: The primary action is clocking in and out. This involves interacting with the facial recognition system and managing their own biometric data.
-   **Faculty**: Focuses on monitoring the attendance of their assigned schedules in real-time and managing exceptions, such as manual clock-in requests.
-   **System Components**: The **BioAttend System** processes all requests, the **Database** stores all persistent data, and the **Real-time Service** (Pusher) handles live notifications between students and faculty.
