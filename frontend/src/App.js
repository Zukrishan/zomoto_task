import { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { WebSocketProvider } from "./context/WebSocketContext";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import TasksPage from "./pages/TasksPage";
import TaskDetailPage from "./pages/TaskDetailPage";
import UsersPage from "./pages/UsersPage";
import TaskLibraryPage from "./pages/TaskLibraryPage";
import CategoriesPage from "./pages/CategoriesPage";
import ReportsPage from "./pages/ReportsPage";
import "./App.css";
import { requestNotificationPermission } from "./firebase";
import api from "./lib/api";

const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/dashboard" replace />;
  }
  
  return children;
};

function AppRoutes() {
  const { user } = useAuth();

  useEffect(() => {
    if (user) {
      requestNotificationPermission().then((token) => {
        if (token) {
          api.post("/fcm-token", { token }).catch(() => {});
        }
      });
    }
  }, [user]);

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/dashboard" replace /> : <LoginPage />} />
      <Route path="/dashboard" element={
        <ProtectedRoute>
          <DashboardPage />
        </ProtectedRoute>
      } />
      <Route path="/tasks" element={
        <ProtectedRoute>
          <TasksPage />
        </ProtectedRoute>
      } />
      <Route path="/tasks/:taskId" element={
        <ProtectedRoute>
          <TaskDetailPage />
        </ProtectedRoute>
      } />
      <Route path="/users" element={
        <ProtectedRoute allowedRoles={["OWNER"]}>
          <UsersPage />
        </ProtectedRoute>
      } />
      <Route path="/task-library" element={
        <ProtectedRoute allowedRoles={["OWNER", "MANAGER"]}>
          <TaskLibraryPage />
        </ProtectedRoute>
      } />
      <Route path="/categories" element={
        <ProtectedRoute allowedRoles={["OWNER", "MANAGER"]}>
          <CategoriesPage />
        </ProtectedRoute>
      } />
      <Route path="/reports" element={
        <ProtectedRoute allowedRoles={["OWNER", "MANAGER"]}>
          <ReportsPage />
        </ProtectedRoute>
      } />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <WebSocketProvider>
          <AppRoutes />
          <Toaster 
            position="top-center" 
            richColors 
            toastOptions={{
              style: { fontFamily: '"DM Sans", sans-serif' }
            }}
          />
        </WebSocketProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
