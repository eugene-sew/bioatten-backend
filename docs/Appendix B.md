# Appendix B: System Setup and Credentials

This appendix provides information on the live demo and the steps to set up the BioAttend system for local development.

## Live Demo

A live, ready-to-use demo version of the application is available at:
**URL**: [http://bioattend.ballotbase.online](http://bioattend.ballotbase.online)

### Getting Started with the Demo

The live demo is provisioned with a single default admin user. To test the full functionality of the application, follow these steps:

**1. Log in as the Admin**

| Role      | Username | Password      |
| :-------- | :------- | :------------ |
| **Admin**   | `admin`  | `adminpass123`  |

**2. Initial Setup (as Admin)**

Once logged in, navigate through the admin dashboard to perform the following actions:

-   **Create a Course**: Go to the course management section and add a new course.
-   **Create a Lecturer (Faculty)**: Go to user management and create a new user with the 'Faculty' role.
-   **Create Students**: Create one or more new users with the 'Student' role.
-   **Assign Lecturer to Course**: Assign the newly created lecturer to the course.
-   **Assign Students to Course**: Assign the students to the same course.

**3. Test Role-Specific Functionality**

After the initial setup, you can log out and sign in as the users you created:

-   **As a Lecturer**: Log in with the faculty account to create schedules for the assigned course and monitor attendance.
-   **As a Student**: Log in with a student account to view your schedule and clock in/out for sessions.

---

## Local Development Setup

### Prerequisites

-   Docker
-   Docker Compose

### 1. Configure Environment Variables

Copy the example environment file to create your local configuration:

```bash
cp .env.example .env
```

Review the `.env` file and fill in any required values, such as Pusher credentials if you intend to use the real-time notification features.

### 2. Build and Run the Application

Use Docker Compose to build the images and run the containers for the backend, frontend, and database:

```bash
docker-compose up --build -d
```

-   The backend will be accessible at `http://localhost:8000`.
-   The frontend will be accessible at `http://localhost:3000`.

### 3. Run Database Migrations

Once the containers are running, execute the database migrations to set up the database schema:

```bash
docker-compose exec backend python manage.py migrate
```

### 4. Create a Superuser (Admin)

Create an administrative user to access the Django admin panel and the application's admin features:

```bash
docker-compose exec backend python manage.py createsuperuser
```

Follow the prompts to set the username, email, and password for the admin account.


