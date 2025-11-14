import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Layout from './components/Layout';

// Pages
import LandingPage from './pages/LandingPage';
import Login from './pages/Login';
import Register from './pages/Register';
import JobSeekerDashboard from './pages/JobSeekerDashboard';
import CompanyDashboard from './pages/CompanyDashboard';
import ChatPage from './pages/ChatPage';
import MatchesPage from './pages/MatchesPage';

// Protected Route Component
const ProtectedRoute = ({ children, requireAuth = true, requireRole = null }) => {
  const { isAuthenticated, user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (requireAuth && !isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!requireAuth && isAuthenticated) {
    // If user is already logged in, redirect to appropriate dashboard
    const dashboardPath = user?.role === 'job_seeker' ? '/dashboard' : '/company-dashboard';
    return <Navigate to={dashboardPath} replace />;
  }

  if (requireRole && user?.role !== requireRole) {
    // Redirect to appropriate dashboard if role doesn't match
    const dashboardPath = user?.role === 'job_seeker' ? '/dashboard' : '/company-dashboard';
    return <Navigate to={dashboardPath} replace />;
  }

  return children;
};

// Main App Component
function AppRoutes() {
  return (
    <Router>
      <Layout>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<LandingPage />} />

          <Route
            path="/login"
            element={
              <ProtectedRoute requireAuth={false}>
                <Login />
              </ProtectedRoute>
            }
          />

          <Route
            path="/register"
            element={
              <ProtectedRoute requireAuth={false}>
                <Register />
              </ProtectedRoute>
            }
          />

          {/* Protected Routes - Job Seeker */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute requireRole="job_seeker">
                <JobSeekerDashboard />
              </ProtectedRoute>
            }
          />

          <Route
            path="/matches"
            element={
              <ProtectedRoute requireRole="job_seeker">
                <MatchesPage />
              </ProtectedRoute>
            }
          />

          {/* Protected Routes - Company */}
          <Route
            path="/company-dashboard"
            element={
              <ProtectedRoute requireRole="company">
                <CompanyDashboard />
              </ProtectedRoute>
            }
          />

          {/* Protected Routes - Common */}
          <Route
            path="/chat"
            element={
              <ProtectedRoute>
                <ChatPage />
              </ProtectedRoute>
            }
          />

          {/* Placeholder Routes */}
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <div className="max-w-4xl mx-auto px-4 py-8">
                  <div className="card">
                    <h1 className="text-2xl font-bold mb-4">Profile</h1>
                    <p className="text-gray-600">Profile page coming soon...</p>
                  </div>
                </div>
              </ProtectedRoute>
            }
          />

          <Route
            path="/jobs"
            element={
              <ProtectedRoute>
                <div className="max-w-7xl mx-auto px-4 py-8">
                  <div className="card">
                    <h1 className="text-2xl font-bold mb-4">Browse Jobs</h1>
                    <p className="text-gray-600">Job listings coming soon...</p>
                  </div>
                </div>
              </ProtectedRoute>
            }
          />

          <Route
            path="/candidates"
            element={
              <ProtectedRoute requireRole="company">
                <div className="max-w-7xl mx-auto px-4 py-8">
                  <div className="card">
                    <h1 className="text-2xl font-bold mb-4">Candidate Pool</h1>
                    <p className="text-gray-600">Candidate browsing coming soon...</p>
                  </div>
                </div>
              </ProtectedRoute>
            }
          />

          <Route
            path="/post-job"
            element={
              <ProtectedRoute requireRole="company">
                <div className="max-w-4xl mx-auto px-4 py-8">
                  <div className="card">
                    <h1 className="text-2xl font-bold mb-4">Post a Job</h1>
                    <p className="text-gray-600">Job posting form coming soon...</p>
                  </div>
                </div>
              </ProtectedRoute>
            }
          />

          {/* Catch-all redirect */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </Router>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}

export default App;
