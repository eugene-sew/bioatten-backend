import axios from 'axios';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    // Get token from localStorage or session storage
    const authStorage = localStorage.getItem('auth-storage');
    
    if (authStorage) {
      try {
        const authData = JSON.parse(authStorage);
        const token = authData?.state?.accessToken;
        
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      } catch (error) {
        console.error('Error parsing auth storage:', error);
      }
    }
    
    // Log request in development
    if (process.env.NODE_ENV === 'development') {
      console.log('API Request:', {
        method: config.method,
        url: config.url,
        params: config.params,
        data: config.data,
      });
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling and token refresh
api.interceptors.response.use(
  (response) => {
    // Log response in development
    if (process.env.NODE_ENV === 'development') {
      console.log('API Response:', {
        url: response.config.url,
        status: response.status,
        data: response.data,
      });
    }
    
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    
    // Log error in development
    if (process.env.NODE_ENV === 'development') {
      console.error('API Error:', {
        url: originalRequest?.url,
        status: error.response?.status,
        message: error.response?.data?.message || error.message,
        data: error.response?.data,
      });
    }
    
    // Handle 401 Unauthorized errors
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      // Try to refresh the token
      const authStorage = localStorage.getItem('auth-storage');
      
      if (authStorage) {
        try {
          const authData = JSON.parse(authStorage);
          const refreshToken = authData?.state?.refreshToken;
          
          if (refreshToken) {
            try {
              const response = await axios.post(
                `${api.defaults.baseURL}/auth/refresh`,
                { refresh_token: refreshToken }
              );
              
              const { access_token } = response.data;
              
              // Update the stored token
              const updatedAuthData = {
                ...authData,
                state: {
                  ...authData.state,
                  accessToken: access_token,
                },
              };
              localStorage.setItem('auth-storage', JSON.stringify(updatedAuthData));
              
              // Retry the original request with new token
              originalRequest.headers.Authorization = `Bearer ${access_token}`;
              return api(originalRequest);
            } catch (refreshError) {
              // Refresh failed, clear auth and redirect to login
              localStorage.removeItem('auth-storage');
              window.location.href = '/login';
              return Promise.reject(refreshError);
            }
          }
        } catch (parseError) {
          console.error('Error parsing auth storage:', parseError);
        }
      }
      
      // No refresh token available, redirect to login
      localStorage.removeItem('auth-storage');
      window.location.href = '/login';
    }
    
    // Handle network errors
    if (!error.response) {
      error.response = {
        data: {
          message: 'Network error. Please check your connection and try again.',
        },
      };
    }
    
    // Handle other HTTP errors
    if (error.response) {
      switch (error.response.status) {
        case 400:
          error.response.data.message = error.response.data.message || 'Bad request. Please check your input.';
          break;
        case 403:
          error.response.data.message = error.response.data.message || 'You do not have permission to perform this action.';
          break;
        case 404:
          error.response.data.message = error.response.data.message || 'The requested resource was not found.';
          break;
        case 422:
          error.response.data.message = error.response.data.message || 'Validation error. Please check your input.';
          break;
        case 500:
          error.response.data.message = error.response.data.message || 'Server error. Please try again later.';
          break;
        default:
          error.response.data.message = error.response.data.message || 'An unexpected error occurred.';
      }
    }
    
    return Promise.reject(error);
  }
);

// Helper functions for common API calls
export const apiHelpers = {
  // Set authorization header manually
  setAuthToken: (token) => {
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete api.defaults.headers.common['Authorization'];
    }
  },
  
  // Remove authorization header
  removeAuthToken: () => {
    delete api.defaults.headers.common['Authorization'];
  },
  
  // Update base URL (useful for environment switching)
  setBaseURL: (url) => {
    api.defaults.baseURL = url;
  },
  
  // Generic error handler
  handleError: (error) => {
    const message = error.response?.data?.message || error.message || 'An error occurred';
    const status = error.response?.status;
    const data = error.response?.data;
    
    return {
      message,
      status,
      data,
      isNetworkError: !error.response,
    };
  },
};

export default api;
