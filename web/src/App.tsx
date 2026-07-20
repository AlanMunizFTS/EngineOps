import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider, useAuth } from "./auth/AuthContext";
import AllProjectsPage from "./pages/AllProjectsPage";
import HomePage from "./pages/HomePage";
import IssueDetailPage from "./pages/IssueDetailPage";
import IssuesPage from "./pages/IssuesPage";
import KanbanPage from "./pages/KanbanPage";
import LoginPage from "./pages/LoginPage";
import MilestonesPage from "./pages/MilestonesPage";
import PhasePage from "./pages/PhasePage";
import ProjectDetailPage from "./pages/ProjectDetailPage";

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { token, isLoading } = useAuth();
  if (isLoading) {
    return null;
  }
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/projects"
        element={
          <ProtectedRoute>
            <HomePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects/all"
        element={
          <ProtectedRoute>
            <AllProjectsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects/:projectId"
        element={
          <ProtectedRoute>
            <ProjectDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects/:projectId/issues"
        element={
          <ProtectedRoute>
            <IssuesPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects/:projectId/issues/:issueId"
        element={
          <ProtectedRoute>
            <IssueDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects/:projectId/kanban"
        element={
          <ProtectedRoute>
            <KanbanPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects/:projectId/milestones"
        element={
          <ProtectedRoute>
            <MilestonesPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects/:projectId/phase/:statusId"
        element={
          <ProtectedRoute>
            <PhasePage />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/projects" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}
