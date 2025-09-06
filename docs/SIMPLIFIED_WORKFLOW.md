# BioAttend Simplified Merged Workflow

This flowchart provides a simplified, high-level overview of the core interactions between user roles and the BioAttend system.

## Simplified Workflow Diagram

```mermaid
graph TD
    subgraph "User Roles"
        A[Admin]
        F[Faculty]
        S[Student]
    end

    subgraph "BioAttend System"
        direction LR
        SYS[BioAttend Application]
        DB[(Database)]
    end

    %% Interactions
    A -- Configures System --> SYS
    S -- Performs Attendance Actions --> SYS
    F -- Monitors & Manages Attendance --> SYS
    
    SYS -- Reads/Writes --> DB

    %% Styling
    classDef user fill:#c9d,stroke:#333,stroke-width:2px;
    classDef system fill:#9c9,stroke:#333,stroke-width:2px;

    class A,F,S user;
    class SYS,DB system;
```

### Core Interactions

1.  **Admin**: Sets up and configures the system (e.g., creates users, schedules, and courses).
2.  **Student**: Interacts with the system primarily to perform attendance actions (e.g., clock-in/out).
3.  **Faculty**: Uses the system to monitor and manage student attendance for their assigned schedules.
4.  **BioAttend System & Database**: All user roles interact with the central **BioAttend Application**, which processes all logic and reads from or writes to the **Database**.
