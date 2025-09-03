import { create } from 'zustand';
import api from '../services/api';

const useAttendanceStore = create((set, get) => ({
  // State
  attendanceRecords: [],
  todayAttendance: [],
  studentAttendance: null,
  attendanceStats: null,
  isLoading: false,
  error: null,
  isMarkingAttendance: false,

  // Actions
  fetchAttendanceRecords: async (params = {}) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.get('/attendance', { params });
      set({
        attendanceRecords: response.data.records,
        isLoading: false,
      });
      return { success: true, data: response.data.records };
    } catch (error) {
      set({ 
        isLoading: false, 
        error: error.response?.data?.message || 'Failed to fetch attendance records' 
      });
      return { success: false, error: error.response?.data?.message };
    }
  },

  fetchTodayAttendance: async (scheduleId = null) => {
    set({ isLoading: true, error: null });
    try {
      const params = scheduleId ? { schedule_id: scheduleId } : {};
      const response = await api.get('/attendance/today', { params });
      set({
        todayAttendance: response.data.records,
        isLoading: false,
      });
      return { success: true, data: response.data.records };
    } catch (error) {
      set({ 
        isLoading: false, 
        error: error.response?.data?.message || 'Failed to fetch today\'s attendance' 
      });
      return { success: false, error: error.response?.data?.message };
    }
  },

  markAttendance: async (attendanceData) => {
    set({ isMarkingAttendance: true, error: null });
    try {
      const response = await api.post('/attendance/mark', attendanceData);
      
      // Update the attendance records if the marked record is for today
      const markedRecord = response.data;
      set((state) => {
        const updatedTodayAttendance = [...state.todayAttendance];
        const existingIndex = updatedTodayAttendance.findIndex(
          record => record.student_id === markedRecord.student_id && 
                   record.schedule_id === markedRecord.schedule_id
        );
        
        if (existingIndex >= 0) {
          updatedTodayAttendance[existingIndex] = markedRecord;
        } else {
          updatedTodayAttendance.push(markedRecord);
        }
        
        return {
          todayAttendance: updatedTodayAttendance,
          isMarkingAttendance: false,
        };
      });
      
      return { success: true, data: markedRecord };
    } catch (error) {
      set({ 
        isMarkingAttendance: false, 
        error: error.response?.data?.message || 'Failed to mark attendance' 
      });
      return { success: false, error: error.response?.data?.message };
    }
  },

  markAttendanceByFingerprint: async (fingerprintData, sessionId) => {
    set({ isMarkingAttendance: true, error: null });
    try {
      const response = await api.post('/attendance/biometric', {
        fingerprint_data: fingerprintData,
        session_id: sessionId,
      });
      
      const markedRecord = response.data;
      set((state) => {
        const updatedTodayAttendance = [...state.todayAttendance];
        const existingIndex = updatedTodayAttendance.findIndex(
          record => record.student_id === markedRecord.student_id && 
                   record.schedule_id === markedRecord.schedule_id
        );
        
        if (existingIndex >= 0) {
          updatedTodayAttendance[existingIndex] = markedRecord;
        } else {
          updatedTodayAttendance.push(markedRecord);
        }
        
        return {
          todayAttendance: updatedTodayAttendance,
          isMarkingAttendance: false,
        };
      });
      
      return { success: true, data: markedRecord };
    } catch (error) {
      set({ 
        isMarkingAttendance: false, 
        error: error.response?.data?.message || 'Failed to mark attendance by fingerprint' 
      });
      return { success: false, error: error.response?.data?.message };
    }
  },

  updateAttendance: async (attendanceId, updateData) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.put(`/attendance/${attendanceId}`, updateData);
      set((state) => ({
        attendanceRecords: state.attendanceRecords.map(record => 
          record.id === attendanceId ? response.data : record
        ),
        todayAttendance: state.todayAttendance.map(record => 
          record.id === attendanceId ? response.data : record
        ),
        isLoading: false,
      }));
      return { success: true, data: response.data };
    } catch (error) {
      set({ 
        isLoading: false, 
        error: error.response?.data?.message || 'Failed to update attendance' 
      });
      return { success: false, error: error.response?.data?.message };
    }
  },

  fetchStudentAttendance: async (studentId, params = {}) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.get(`/students/${studentId}/attendance`, { params });
      set({
        studentAttendance: response.data,
        isLoading: false,
      });
      return { success: true, data: response.data };
    } catch (error) {
      set({ 
        isLoading: false, 
        error: error.response?.data?.message || 'Failed to fetch student attendance' 
      });
      return { success: false, error: error.response?.data?.message };
    }
  },

  fetchAttendanceStats: async (params = {}) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.get('/attendance/stats', { params });
      set({
        attendanceStats: response.data,
        isLoading: false,
      });
      return { success: true, data: response.data };
    } catch (error) {
      set({ 
        isLoading: false, 
        error: error.response?.data?.message || 'Failed to fetch attendance statistics' 
      });
      return { success: false, error: error.response?.data?.message };
    }
  },

  generateAttendanceReport: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.post('/attendance/report', params, {
        responseType: 'blob',
      });
      
      // Create a download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `attendance_report_${Date.now()}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      set({ isLoading: false });
      return { success: true };
    } catch (error) {
      set({ 
        isLoading: false, 
        error: error.response?.data?.message || 'Failed to generate report' 
      });
      return { success: false, error: error.response?.data?.message };
    }
  },

  exportAttendanceData: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.get('/attendance/export', { 
        params,
        responseType: 'blob',
      });
      
      // Create a download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `attendance_export_${Date.now()}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      set({ isLoading: false });
      return { success: true };
    } catch (error) {
      set({ 
        isLoading: false, 
        error: error.response?.data?.message || 'Failed to export data' 
      });
      return { success: false, error: error.response?.data?.message };
    }
  },

  clearError: () => set({ error: null }),
  clearStudentAttendance: () => set({ studentAttendance: null }),
}));

export default useAttendanceStore;
