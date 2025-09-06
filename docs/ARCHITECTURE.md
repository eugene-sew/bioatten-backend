# BioAttend High-Level Architecture

This document provides a high-level overview of the BioAttend application architecture, illustrating the main components and their interactions.

## System Flowchart

```mermaid
graph TD
    subgraph Users
        A[Student]
        B[Faculty/Lecturer]
        C[Admin]
    end

    subgraph "Frontend (React SPA)"
        D[User Interface]
        E[API Client]
        F[Real-time Listener]
    end

    subgraph "Backend (Django REST Framework)"
        G[API Endpoints]
        H[Business Logic]
        I[Authentication & Permissions]
        J[Facial Recognition Module]
    end

    subgraph Services
        K[Database (PostgreSQL)]
        L[Pusher Service]
    end

    %% User Interactions
    A --> D
    B --> D
    C --> D

    %% Frontend to Backend Communication
    D -- User Actions --> E
    E -- REST API Calls --> G

    %% Backend Logic
    G --> H
    G --> I
    H -- CRUD Operations --> K
    H -- Face Processing --> J
    J -- Stores/Retrieves Embeddings --> K
    I -- Validates Credentials --> K

    %% Real-time Notifications
    H -- Triggers Events --> L
    L -- Pushes Notifications --> F
    F -- Updates UI --> D

    %% Styling
    classDef user fill:#c9d,stroke:#333,stroke-width:2px;
    classDef frontend fill:#9cf,stroke:#333,stroke-width:2px;
    classDef backend fill:#f96,stroke:#333,stroke-width:2px;
    classDef service fill:#9c9,stroke:#333,stroke-width:2px;

    class A,B,C user;
    class D,E,F frontend;
    class G,H,I,J backend;
    class K,L service;
```

### Component Descriptions

- **Users**: Represents the different roles interacting with the system (Student, Faculty, Admin).
- **Frontend (React SPA)**: The single-page application that provides the user interface. It communicates with the backend via API calls and listens for real-time updates.
- **Backend (Django REST Framework)**: The core of the application. It handles all business logic, manages data, authenticates users, and integrates with external services.
- **Facial Recognition Module**: An integrated part of the backend responsible for processing images, creating facial embeddings for enrollment, and verifying faces for attendance.
- **Database (PostgreSQL)**: The primary data store for all application information, including user profiles, course schedules, attendance logs, and facial embeddings.
- **Pusher Service**: A third-party service used to push real-time notifications from the backend to the frontend, enabling features like live attendance updates and manual clock-in requests for lecturers.
