# Authentication System Documentation

## Overview

This authentication system provides role-based access control (RBAC) with three user roles:
- **ADMIN**: Full system access
- **STUDENT**: Student-specific access
- **FACULTY**: Faculty/teacher access

## API Endpoints

### Authentication Endpoints

1. **User Registration** (Admin only)
   - `POST /api/auth/register/`
   - Body: `{"email": "user@example.com", "password": "pass123", "password_confirm": "pass123", "first_name": "John", "last_name": "Doe", "role": "STUDENT"}`

2. **Login**
   - `POST /api/auth/login/`
   - Body: `{"email": "user@example.com", "password": "pass123"}`
   - Returns: `{"access": "...", "refresh": "...", "user": {...}}`

3. **Token Refresh**
   - `POST /api/auth/token/refresh/`
   - Body: `{"refresh": "..."}`
   - Returns: `{"access": "..."}`

4. **Logout**
   - `POST /api/auth/logout/`
   - Headers: `Authorization: Bearer <access_token>`
   - Body: `{"refresh_token": "..."}`

### Password Management

1. **Request Password Reset**
   - `POST /api/auth/password-reset/`
   - Body: `{"email": "user@example.com"}`

2. **Confirm Password Reset**
   - `POST /api/auth/password-reset-confirm/`
   - Body: `{"token": "...", "new_password": "newpass123", "confirm_password": "newpass123"}`

3. **Change Password** (Authenticated users)
   - `POST /api/auth/change-password/`
   - Headers: `Authorization: Bearer <access_token>`
   - Body: `{"old_password": "oldpass", "new_password": "newpass", "confirm_password": "newpass"}`

### User Management

1. **List Users** (Admin only)
   - `GET /api/auth/users/`
   - Query params: `?role=STUDENT` (optional)

2. **Get User Details**
   - `GET /api/auth/users/{user_id}/` or `GET /api/auth/users/me/`
   - Headers: `Authorization: Bearer <access_token>`

3. **Update User**
   - `PATCH /api/auth/users/{user_id}/`
   - Headers: `Authorization: Bearer <access_token>`

4. **Delete User** (Admin only)
   - `DELETE /api/auth/users/{user_id}/`
   - Headers: `Authorization: Bearer <access_token>`

## Using Permissions in Your Views

### Available Permission Classes

```python
from authentication.permissions import (
    IsAdmin,              # Only admin users
    IsStudent,            # Only student users
    IsFaculty,            # Only faculty users
    IsAdminOrFaculty,     # Admin or faculty users
    IsOwnerOrAdmin,       # Object owner or admin
    IsOwnerOrReadOnly,    # Read all, write only owner/admin
    IsAuthenticatedAndActive  # Authenticated and active users
)
```

### Example Usage in Views

```python
from rest_framework import generics
from authentication.permissions import IsAdmin, IsAdminOrFaculty

# Admin-only view
class AdminOnlyView(generics.ListAPIView):
    permission_classes = [IsAdmin]
    # ...

# Faculty or Admin view
class FacultyView(generics.ListCreateAPIView):
    permission_classes = [IsAdminOrFaculty]
    # ...

# View with object-level permissions
class StudentProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsOwnerOrAdmin]
    
    def get_object(self):
        obj = super().get_object()
        self.check_object_permissions(self.request, obj)
        return obj
```

### Function-based Views

```python
from rest_framework.decorators import api_view, permission_classes
from authentication.permissions import IsStudent

@api_view(['GET'])
@permission_classes([IsStudent])
def student_only_view(request):
    # Only students can access this
    return Response({'message': 'Student data'})
```

## Management Commands

Create an admin user:
```bash
python manage.py create_admin
# Or with arguments:
python manage.py create_admin --email admin@example.com --first-name Admin --last-name User
```

## Environment Variables

Add these to your `.env` file:

```env
# Email configuration (for password reset)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@bioattend.com
```

## Notes

1. The default permission for all API endpoints is `IsAuthenticated` (set in settings.py)
2. JWT tokens expire after 60 minutes (configurable in settings.py)
3. Refresh tokens expire after 7 days
4. Password reset tokens expire after 24 hours
5. In DEBUG mode, emails are printed to console instead of being sent
