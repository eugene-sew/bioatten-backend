import time
import requests
from django.db import connection
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from authentication.permissions import IsAdmin


@api_view(['GET'])
@permission_classes([AllowAny])
def system_health(request):
    """Comprehensive system health check endpoint."""
    
    health_status = {
        'timestamp': timezone.now().isoformat(),
        'overall_status': 'healthy',
        'services': {}
    }
    
    # Check API Server
    api_status = check_api_server()
    health_status['services']['api_server'] = api_status
    
    # Check Database
    db_status = check_database()
    health_status['services']['database'] = db_status
    
    # Check Biometric System
    biometric_status = check_biometric_system()
    health_status['services']['biometric_devices'] = biometric_status
    
    # Check Cache (Redis/Memory)
    cache_status = check_cache()
    health_status['services']['cache'] = cache_status
    
    # Determine overall status
    all_services = [api_status, db_status, biometric_status, cache_status]
    if any(service['status'] == 'critical' for service in all_services):
        health_status['overall_status'] = 'critical'
    elif any(service['status'] == 'warning' for service in all_services):
        health_status['overall_status'] = 'warning'
    
    # Return appropriate HTTP status
    http_status = status.HTTP_200_OK
    if health_status['overall_status'] == 'critical':
        http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    elif health_status['overall_status'] == 'warning':
        http_status = status.HTTP_200_OK  # Still operational
    
    return Response(health_status, status=http_status)


def check_api_server():
    """Check API server health."""
    try:
        start_time = time.time()
        
        # Basic server checks
        response_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Check if we can process requests
        test_query_time = time.time()
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user_count = User.objects.count()
        query_time = (time.time() - test_query_time) * 1000
        
        status_level = 'healthy'
        message = 'API server is operational'
        
        if response_time > 1000:  # > 1 second
            status_level = 'warning'
            message = 'API server response time is slow'
        elif response_time > 5000:  # > 5 seconds
            status_level = 'critical'
            message = 'API server response time is critically slow'
        
        return {
            'status': status_level,
            'message': message,
            'details': {
                'response_time_ms': round(response_time, 2),
                'query_time_ms': round(query_time, 2),
                'user_count': user_count,
                'uptime': 'Available'
            }
        }
    except Exception as e:
        return {
            'status': 'critical',
            'message': f'API server error: {str(e)}',
            'details': {
                'error': str(e)
            }
        }


def check_database():
    """Check database connection and performance."""
    try:
        start_time = time.time()
        
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        # Test a simple query
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user_count = User.objects.count()
        
        query_time = (time.time() - start_time) * 1000
        
        # Check database performance
        status_level = 'healthy'
        message = 'Database is connected and responsive'
        
        if query_time > 500:  # > 500ms
            status_level = 'warning'
            message = 'Database queries are slow'
        elif query_time > 2000:  # > 2 seconds
            status_level = 'critical'
            message = 'Database queries are critically slow'
        
        return {
            'status': status_level,
            'message': message,
            'details': {
                'connection': 'Connected',
                'query_time_ms': round(query_time, 2),
                'total_users': user_count,
                'database_engine': connection.vendor
            }
        }
    except Exception as e:
        return {
            'status': 'critical',
            'message': f'Database connection failed: {str(e)}',
            'details': {
                'error': str(e),
                'connection': 'Failed'
            }
        }


def check_biometric_system():
    """Check biometric system health."""
    try:
        # Check if facial recognition API is accessible
        facial_api_url = getattr(settings, 'FACIAL_RECOGNITION_API_URL', 'http://127.0.0.1:5000')
        
        start_time = time.time()
        
        try:
            # Try to reach the facial recognition service
            response = requests.get(f"{facial_api_url}/health", timeout=5)
            api_response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                status_level = 'healthy'
                message = 'All biometric devices are online'
                
                if api_response_time > 1000:
                    status_level = 'warning'
                    message = 'Biometric system is slow but operational'
                
                return {
                    'status': status_level,
                    'message': message,
                    'details': {
                        'facial_api': 'Online',
                        'response_time_ms': round(api_response_time, 2),
                        'devices_count': 1,  # Assuming 1 facial recognition system
                        'last_check': timezone.now().isoformat()
                    }
                }
            else:
                return {
                    'status': 'warning',
                    'message': 'Biometric API returned error status',
                    'details': {
                        'facial_api': 'Error',
                        'status_code': response.status_code,
                        'response_time_ms': round(api_response_time, 2)
                    }
                }
        except requests.exceptions.ConnectionError:
            return {
                'status': 'warning',
                'message': 'Biometric system is offline',
                'details': {
                    'facial_api': 'Offline',
                    'error': 'Connection refused',
                    'note': 'System can operate without biometric features'
                }
            }
        except requests.exceptions.Timeout:
            return {
                'status': 'warning',
                'message': 'Biometric system timeout',
                'details': {
                    'facial_api': 'Timeout',
                    'error': 'Request timeout after 5 seconds'
                }
            }
    except Exception as e:
        return {
            'status': 'warning',
            'message': f'Biometric system check failed: {str(e)}',
            'details': {
                'error': str(e),
                'note': 'Manual attendance is still available'
            }
        }


def check_cache():
    """Check cache system health."""
    try:
        start_time = time.time()
        
        # Test cache write/read
        test_key = 'health_check_test'
        test_value = f'test_{int(time.time())}'
        
        cache.set(test_key, test_value, timeout=60)
        retrieved_value = cache.get(test_key)
        
        cache_time = (time.time() - start_time) * 1000
        
        if retrieved_value == test_value:
            status_level = 'healthy'
            message = 'Cache system is operational'
            
            if cache_time > 100:  # > 100ms
                status_level = 'warning'
                message = 'Cache system is slow'
            
            # Clean up test key
            cache.delete(test_key)
            
            return {
                'status': status_level,
                'message': message,
                'details': {
                    'cache_backend': cache.__class__.__name__,
                    'response_time_ms': round(cache_time, 2),
                    'read_write': 'Working'
                }
            }
        else:
            return {
                'status': 'warning',
                'message': 'Cache read/write test failed',
                'details': {
                    'cache_backend': cache.__class__.__name__,
                    'read_write': 'Failed'
                }
            }
    except Exception as e:
        return {
            'status': 'warning',
            'message': f'Cache system error: {str(e)}',
            'details': {
                'error': str(e),
                'note': 'Application can run without cache'
            }
        }


@api_view(['GET'])
@permission_classes([AllowAny])
def quick_health(request):
    """Quick health check for load balancers."""
    try:
        # Quick database check
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        return Response({
            'status': 'healthy',
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        return Response({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
