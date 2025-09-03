from django.urls import path
from .views import (
    UserRegistrationView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    UserListView,
    UserDetailView,
    password_reset_request,
    password_reset_confirm,
    change_password,
    logout
)

app_name = 'authentication'

urlpatterns = [
    # Authentication endpoints
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', logout, name='logout'),
    
    # Password management
    path('password-reset/', password_reset_request, name='password_reset_request'),
    path('password-reset-confirm/', password_reset_confirm, name='password_reset_confirm'),
    path('change-password/', change_password, name='change_password'),
    
    # User management
    path('users/', UserListView.as_view(), name='user_list'),
    path('users/<str:pk>/', UserDetailView.as_view(), name='user_detail'),
]
