import { create } from 'zustand';
import api from '../services/api';

const useScheduleStore = create((set, get) => ({
  // State
  schedules: [],
  todaySchedule: [],
  weekSchedule: [],
  selectedSchedule: null,
  isLoading: false,
  error: null,
  currentSession: null,

  // Actions
  fetchSchedules: async (params = {}) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.get('/schedules', { params });
      set({
        schedules: response.data.schedules,
        isLoading: false,
      });
      return { success: true, data: response.data.schedules };
    } catch (error) {
      set({ 
        isLoading: false, 
        error: error.response?.data?.message || 'Failed to fetch schedules' 
      });
      return { success: false, error: error.response?.data?.message };
    }
  },

  fetchTodaySchedule: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.get('/schedules/today');
      set({
        todaySchedule: response.data.schedules,
        isLoading: false,
      });
      return { success: true, data: response.data.schedules };
    } catch (error) {
      set({ 
        isLoading: false, 
        error: error.response?.data?.message || 'Failed to fetch today\'s schedule' 
      });
      return { success: false, error: error.response?.data?.message };
    }
  },

  fetchWeekSchedule: async (weekStart) => {
    set({ isLoading: true, error: null });
    try {
      const params = weekStart ? { week_start: weekStart } : {};
      const response = await api.get('/schedules/week', { params });
      set({
        weekSchedule: response.data.schedules,
        isLoading: false,
      });
      return { success: true, data: response.data.schedules };
    } catch (error) {
      set({ 
        isLoading: false, 
        error: error.response?.data?.message || 'Failed to fetch week schedule' 
      });
      return { success: false, error: error.response?.data?.message };
    }
  },

  fetchScheduleById: async (scheduleId) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.get(`/schedules/${scheduleId}`);
      set({ 
        selectedSchedule: response.data,
        isLoading: false 
      });
      return { success: true, data: response.data };
    } catch (error) {
      set({ 
        isLoading: false, 
        error: error.response?.data?.message || 'Failed to fetch schedule' 
      });
      return { success: false, error: error.response?.data?.message };
    }
  },

  createSchedule: async (scheduleData) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.post('/schedules', scheduleData);
      set((state) => ({
        schedules: [...state.schedules, response.data],
        isLoading: false,
      }));
      return { success: true, data: response.data };
    } catch (error) {
      set({ 
        isLoading: false, 
        error: error.response?.data?.message || 'Failed to create schedule' 
      });
      return { success: false, error: error.response?.data?.message };
    }
  },

  updateSchedule: async (scheduleId, scheduleData) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.put(`/schedules/${scheduleId}`, scheduleData);
      set((state) => ({
        schedules: state.schedules.map(schedule => 
          schedule.id === scheduleId ? response.data : schedule
        ),
        selectedSchedule: state.selectedSchedule?.id === scheduleId 
          ? response.data 
          : state.selectedSchedule,
        isLoading: false,
      }));
      return { success: true, data: response.data };
    } catch (error) {
      set({ 
        isLoading: false, 
        error: error.response?.data?.message || 'Failed to update schedule' 
      });
      return { success: false, error: error.response?.data?.message };
    }
  },

  deleteSchedule: async (scheduleId) => {
    set({ isLoading: true, error: null });
    try {
      await api.delete(`/schedules/${scheduleId}`);
      set((state) => ({
        schedules: state.schedules.filter(schedule => schedule.id !== scheduleId),
        selectedSchedule: state.selectedSchedule?.id === scheduleId 
          ? null 
          : state.selectedSchedule,
        isLoading: false,
      }));
      return { success: true };
    } catch (error) {
      set({ 
        isLoading: false, 
        error: error.response?.data?.message || 'Failed to delete schedule' 
      });
      return { success: false, error: error.response?.data?.message };
    }
  },

  startSession: async (scheduleId) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.post(`/schedules/${scheduleId}/start-session`);
      set({ 
        currentSession: response.data,
        isLoading: false 
      });
      return { success: true, data: response.data };
    } catch (error) {
      set({ 
        isLoading: false, 
        error: error.response?.data?.message || 'Failed to start session' 
      });
      return { success: false, error: error.response?.data?.message };
    }
  },

  endSession: async (sessionId) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.post(`/sessions/${sessionId}/end`);
      set({ 
        currentSession: null,
        isLoading: false 
      });
      return { success: true, data: response.data };
    } catch (error) {
      set({ 
        isLoading: false, 
        error: error.response?.data?.message || 'Failed to end session' 
      });
      return { success: false, error: error.response?.data?.message };
    }
  },

  getCurrentSession: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.get('/sessions/current');
      set({ 
        currentSession: response.data,
        isLoading: false 
      });
      return { success: true, data: response.data };
    } catch (error) {
      if (error.response?.status === 404) {
        // No current session
        set({ 
          currentSession: null,
          isLoading: false 
        });
        return { success: true, data: null };
      }
      set({ 
        isLoading: false, 
        error: error.response?.data?.message || 'Failed to fetch current session' 
      });
      return { success: false, error: error.response?.data?.message };
    }
  },

  clearError: () => set({ error: null }),
  clearSelectedSchedule: () => set({ selectedSchedule: null }),
}));

export default useScheduleStore;
