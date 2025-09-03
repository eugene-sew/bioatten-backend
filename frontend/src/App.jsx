import { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import useAuthStore from '@/store/authStore';

// Layouts
import AdminLayout from '@/layouts/AdminLayout';

// Components
import ProtectedRoute from '@/components/ProtectedRoute';

// Admin Pages
import Dashboard from '@/pages/admin/Dashboard';
import Students from '@/pages/admin/Students';
import EnrollStudent from '@/pages/admin/EnrollStudent';
import Groups from '@/pages/admin/Groups';
import Schedules from '@/pages/admin/Schedules';
import LiveAttendance from '@/pages/admin/LiveAttendance';
import Reports from '@/pages/admin/Reports';

// Auth Pages (to be created)
const Login = () => (
  <div className="min-h-screen bg-gray-100 flex items-center justify-center">
    <div className="bg-white p-8 rounded-lg shadow-md">
      <h1 className="text-2xl font-bold text-gray-800 mb-4">Login</h1>
      <p className="text-gray-600">Login page to be implemented</p>
    </div>
  </div>
);

const Unauthorized = () => (
  <div className="min-h-screen bg-gray-100 flex items-center justify-center">
    <div className="bg-white p-8 rounded-lg shadow-md">
      <h1 className="text-2xl font-bold text-red-600 mb-4">Unauthorized</h1>
      <p className="text-gray-600">You don't have permission to access this page.</p>
    </div>
  </div>
);

function App() {
  const { checkAuth } = useAuthStore();

  useEffect(() => {
    // Check authentication status on app load
    checkAuth();
  }, [checkAuth]);

  return (
    <Router>
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/unauthorized" element={<Unauthorized />} />

        {/* Admin Routes */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute requiredRole="admin">
              <AdminLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/admin/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="students" element={<Students />} />
          <Route path="enroll" element={<EnrollStudent />} />
          <Route path="groups" element={<Groups />} />
          <Route path="schedules" element={<Schedules />} />
          <Route path="attendance" element={<LiveAttendance />} />
          <Route path="reports" element={<Reports />} />
        </Route>

        {/* Default Route */}
        <Route path="/" element={<Navigate to="/admin/dashboard" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
