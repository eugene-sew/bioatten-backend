import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import api from '../services/api';

const useAuthStore = create(
  persist(
    (set, get) => ({
      // State
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // Actions
      setTokens: (accessToken, refreshToken) => {
        set({
          accessToken,
          refreshToken,
          isAuthenticated: !!accessToken,
        });
      },

      setUser: (user) => {
        set({ user });
      },

      login: async (email, password) => {
        set({ isLoading: true, error: null });
        try {
          const response = await api.post('/auth/login', { email, password });
          const { access_token, refresh_token, user } = response.data;
          
          get().setTokens(access_token, refresh_token);
          get().setUser(user);
          
          // Set the token in the API instance
          api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
          
          set({ isLoading: false });
          return { success: true };
        } catch (error) {
          set({ 
            isLoading: false, 
            error: error.response?.data?.message || 'Login failed' 
          });
          return { success: false, error: error.response?.data?.message };
        }
      },

      register: async (userData) => {
        set({ isLoading: true, error: null });
        try {
          const response = await api.post('/auth/register', userData);
          const { access_token, refresh_token, user } = response.data;
          
          get().setTokens(access_token, refresh_token);
          get().setUser(user);
          
          api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
          
          set({ isLoading: false });
          return { success: true };
        } catch (error) {
          set({ 
            isLoading: false, 
            error: error.response?.data?.message || 'Registration failed' 
          });
          return { success: false, error: error.response?.data?.message };
        }
      },

      logout: () => {
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          error: null,
        });
        delete api.defaults.headers.common['Authorization'];
      },

      refreshAccessToken: async () => {
        const { refreshToken } = get();
        if (!refreshToken) {
          get().logout();
          return null;
        }

        try {
          const response = await api.post('/auth/refresh', {
            refresh_token: refreshToken,
          });
          const { access_token } = response.data;
          
          set({ accessToken: access_token });
          api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
          
          return access_token;
        } catch (error) {
          get().logout();
          return null;
        }
      },

      checkAuth: async () => {
        const { accessToken } = get();
        if (!accessToken) {
          return false;
        }

        set({ isLoading: true });
        try {
          const response = await api.get('/auth/me');
          get().setUser(response.data);
          set({ isLoading: false, isAuthenticated: true });
          return true;
        } catch (error) {
          if (error.response?.status === 401) {
            // Try to refresh the token
            const newToken = await get().refreshAccessToken();
            if (newToken) {
              // Retry the request
              try {
                const response = await api.get('/auth/me');
                get().setUser(response.data);
                set({ isLoading: false, isAuthenticated: true });
                return true;
              } catch (retryError) {
                get().logout();
                set({ isLoading: false });
                return false;
              }
            }
          }
          get().logout();
          set({ isLoading: false });
          return false;
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

export default useAuthStore;
