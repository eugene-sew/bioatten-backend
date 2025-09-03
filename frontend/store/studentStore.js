import { create } from 'zustand';
import api from '../services/api';

const useStudentStore = create((set, get) => ({
  // State
  students: [],
  selectedStudent: null,
  isLoading: false,
  error: null,
  pagination: {
    page: 1,
    limit: 20,
    total: 0,
    totalPages: 0,
  },

  // Actions
  fetchStudents: async (params = {}) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.get('/students', { params });
      set({
        students: response.data.students,
        pagination: {
          page: response.data.page,
          limit: response.data.limit,
          total: response.data.total,
          totalPages: response.data.total_pages,
        },
        isLoading: false,
      });
      return { success: true };
    } catch (error) {
      set({ 
        isLoading: false, 
        error: error.response?.data?.message || 'Failed to fetch students' 
      });
      return { success: false, error: error.response?.data?.message };
    }
  },

  fetchStudentById: async (studentId) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.get(`/students/${studentId}`);
      set({ 
        selectedStudent: response.data,
        isLoading: false 
      });
      return { success: true, data: response.data };
    } catch (error) {
      set({ 
        isLoading: false, 
        error: error.response?.data?.message || 'Failed to fetch student' 
      });
      return { success: false, error: error.response?.data?.message };
    }
  },

  createStudent: async (studentData) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.post('/students', studentData);
      set((state) => ({
        students: [...state.students, response.data],
        isLoading: false,
      }));
      return { success: true, data: response.data };
    } catch (error) {
      set({ 
        isLoading: false, 
        error: error.response?.data?.message || 'Failed to create student' 
      });
      return { success: false, error: error.response?.data?.message };
    }
  },

  updateStudent: async (studentId, studentData) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.put(`/students/${studentId}`, studentData);
      set((state) => ({
        students: state.students.map(student => 
          student.id === studentId ? response.data : student
        ),
        selectedStudent: state.selectedStudent?.id === studentId 
          ? response.data 
          : state.selectedStudent,
        isLoading: false,
      }));
      return { success: true, data: response.data };
    } catch (error) {
      set({ 
        isLoading: false, 
        error: error.response?.data?.message || 'Failed to update student' 
      });
      return { success: false, error: error.response?.data?.message };
    }
  },

  deleteStudent: async (studentId) => {
    set({ isLoading: true, error: null });
    try {
      await api.delete(`/students/${studentId}`);
      set((state) => ({
        students: state.students.filter(student => student.id !== studentId),
        selectedStudent: state.selectedStudent?.id === studentId 
          ? null 
          : state.selectedStudent,
        isLoading: false,
      }));
      return { success: true };
    } catch (error) {
      set({ 
        isLoading: false, 
        error: error.response?.data?.message || 'Failed to delete student' 
      });
      return { success: false, error: error.response?.data?.message };
    }
  },

  enrollFingerprint: async (studentId, fingerprintData) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.post(`/students/${studentId}/fingerprint`, {
        fingerprint_data: fingerprintData,
      });
      set((state) => ({
        students: state.students.map(student => 
          student.id === studentId 
            ? { ...student, fingerprint_enrolled: true }
            : student
        ),
        selectedStudent: state.selectedStudent?.id === studentId 
          ? { ...state.selectedStudent, fingerprint_enrolled: true }
          : state.selectedStudent,
        isLoading: false,
      }));
      return { success: true, data: response.data };
    } catch (error) {
      set({ 
        isLoading: false, 
        error: error.response?.data?.message || 'Failed to enroll fingerprint' 
      });
      return { success: false, error: error.response?.data?.message };
    }
  },

  searchStudents: async (query) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.get('/students/search', { 
        params: { q: query } 
      });
      set({ 
        students: response.data.students,
        isLoading: false 
      });
      return { success: true, data: response.data.students };
    } catch (error) {
      set({ 
        isLoading: false, 
        error: error.response?.data?.message || 'Search failed' 
      });
      return { success: false, error: error.response?.data?.message };
    }
  },

  clearError: () => set({ error: null }),
  clearSelectedStudent: () => set({ selectedStudent: null }),
}));

export default useStudentStore;
