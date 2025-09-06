import json
import logging
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import UserActivity

User = get_user_model()
logger = logging.getLogger(__name__)


class ActivityTrackingMiddleware(MiddlewareMixin):
    """Middleware to track user activities across the system."""
    
    # Paths to ignore for activity tracking
    IGNORED_PATHS = [
        '/admin/jsi18n/',
        '/static/',
        '/media/',
        '/favicon.ico',
        '/api/auth/token/refresh/',
        '/api/activities/',  # Avoid infinite loops
    ]
    
    # Methods to track
    TRACKED_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE']
    
    # Path mappings to action types and descriptions
    PATH_MAPPINGS = {
        '/api/auth/login/': {
            'action_type': 'login',
            'description': 'User logged in'
        },
        '/api/auth/logout/': {
            'action_type': 'logout',
            'description': 'User logged out'
        },
        '/api/attendance/clock-in/': {
            'action_type': 'check_in',
            'description': 'Clocked in for attendance'
        },
        '/api/attendance/clock-out/': {
            'action_type': 'check_out',
            'description': 'Clocked out from attendance'
        },
        '/api/facial/enroll/': {
            'action_type': 'enroll',
            'description': 'Completed biometric enrollment'
        },
        '/api/auth/users/': {
            'POST': {
                'action_type': 'user_create',
                'description': 'Created new user account'
            }
        },
        '/api/students/groups/': {
            'POST': {
                'action_type': 'group_create',
                'description': 'Created new student group'
            }
        },
        '/api/faculty/schedules/': {
            'POST': {
                'action_type': 'schedule_create',
                'description': 'Created new schedule'
            }
        },
    }

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_response(self, request, response):
        """Process the response and log activity if applicable."""
        try:
            # Skip if user is not authenticated
            if not hasattr(request, 'user') or not request.user.is_authenticated:
                return response
            
            # Skip ignored paths
            if any(ignored in request.path for ignored in self.IGNORED_PATHS):
                return response
            
            # Only track certain methods or successful responses
            should_track = (
                request.method in self.TRACKED_METHODS or 
                request.path in self.PATH_MAPPINGS
            ) and 200 <= response.status_code < 400
            
            if should_track:
                self._log_activity(request, response)
                
        except Exception as e:
            # Log error but don't break the response
            logger.error(f"Error in ActivityTrackingMiddleware: {e}")
        
        return response

    def _log_activity(self, request, response):
        """Log the user activity."""
        try:
            # Get client IP
            ip_address = self._get_client_ip(request)
            
            # Get user agent
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            
            # Determine action type and description
            action_info = self._get_action_info(request, response)
            
            if action_info:
                # Create activity record
                UserActivity.objects.create(
                    user=request.user,
                    action_type=action_info['action_type'],
                    description=action_info['description'],
                    ip_address=ip_address,
                    user_agent=user_agent,
                    request_path=request.path,
                    request_method=request.method,
                    target_model=action_info.get('target_model'),
                    target_id=action_info.get('target_id'),
                    extra_data=action_info.get('extra_data', {})
                )
                
        except Exception as e:
            logger.error(f"Error logging activity: {e}")

    def _get_client_ip(self, request):
        """Get the client's IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def _get_action_info(self, request, response):
        """Determine the action type and description based on the request."""
        path = request.path
        method = request.method
        
        # Check exact path matches first
        if path in self.PATH_MAPPINGS:
            mapping = self.PATH_MAPPINGS[path]
            if isinstance(mapping, dict) and method in mapping:
                return mapping[method]
            elif isinstance(mapping, dict) and 'action_type' in mapping:
                return mapping
        
        # Check path patterns
        if '/api/auth/users/' in path and method == 'PUT':
            return {
                'action_type': 'update',
                'description': 'Updated user profile',
                'target_model': 'User'
            }
        
        if '/api/students/groups/' in path and method == 'PUT':
            return {
                'action_type': 'update',
                'description': 'Updated student group',
                'target_model': 'StudentGroup'
            }
        
        if '/api/faculty/schedules/' in path and method == 'PUT':
            return {
                'action_type': 'update',
                'description': 'Updated schedule',
                'target_model': 'Schedule'
            }
        
        if '/api/attendance/' in path and method == 'POST':
            return {
                'action_type': 'attendance_mark',
                'description': 'Marked attendance',
                'target_model': 'Attendance'
            }
        
        # Generic mappings for CRUD operations
        if method == 'POST':
            return {
                'action_type': 'create',
                'description': f'Created new resource at {path}'
            }
        elif method == 'PUT' or method == 'PATCH':
            return {
                'action_type': 'update',
                'description': f'Updated resource at {path}'
            }
        elif method == 'DELETE':
            return {
                'action_type': 'delete',
                'description': f'Deleted resource at {path}'
            }
        
        return None


class ActivityLoggerMixin:
    """Mixin to add activity logging to views."""
    
    def log_activity(self, action_type, description, **kwargs):
        """Helper method to log custom activities."""
        if hasattr(self.request, 'user') and self.request.user.is_authenticated:
            try:
                UserActivity.objects.create(
                    user=self.request.user,
                    action_type=action_type,
                    description=description,
                    ip_address=self._get_client_ip(),
                    user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
                    request_path=self.request.path,
                    request_method=self.request.method,
                    **kwargs
                )
            except Exception as e:
                logger.error(f"Error logging custom activity: {e}")
    
    def _get_client_ip(self):
        """Get the client's IP address."""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip
