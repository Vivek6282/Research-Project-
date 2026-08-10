/**
 * Trackside — Main App Component
 *
 * Sets up routing with role-based dashboard redirection.
 * AuthProvider wraps everything so auth state is available everywhere.
 * Routes are protected — unauthenticated users are redirected to /login.
 */

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./lib/auth";
import { PreferencesProvider } from "./context/PreferencesContext";
import { LoginPage } from "./pages/login";
import { CoachDashboard } from "./pages/coach";
import { AdminDashboard } from "./pages/admin";
import { DriverDashboard } from "./pages/driver";

/**
 * ProtectedRoute — redirects to /login if the user isn't authenticated.
 * If the user is authenticated but on the wrong route, redirects to
 * their role-specific dashboard.
 */
function ProtectedRoute({
  role,
  children,
}: {
  role: string;
  children: React.ReactNode;
}) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{ background: "var(--color-bg)" }}
      >
        <div className="text-center">
          <div className="flex justify-center mb-3">
            <div className="flex gap-1">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="w-2 h-2 rounded-full animate-pulse-glow"
                  style={{
                    background: "var(--color-accent)",
                    animationDelay: `${i * 200}ms`,
                  }}
                />
              ))}
            </div>
          </div>
          <p className="text-xs font-mono" style={{ color: "var(--color-muted)" }}>
            Loading…
          </p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (user.role !== role) {
    return <Navigate to={`/${user.role}`} replace />;
  }

  return <>{children}</>;
}

/**
 * LoginRoute — redirects authenticated users to their dashboard.
 */
function LoginRoute() {
  const { user, isLoading } = useAuth();

  if (isLoading) return null;

  if (user) {
    return <Navigate to={`/${user.role}`} replace />;
  }

  return <LoginPage />;
}

function AppRoutes() {
  return (
    <Routes>
      {/* Login — the only public route */}
      <Route path="/login" element={<LoginRoute />} />

      {/* Role-based dashboards — protected */}
      <Route
        path="/coach"
        element={
          <ProtectedRoute role="coach">
            <CoachDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <ProtectedRoute role="admin">
            <AdminDashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/driver"
        element={
          <ProtectedRoute role="driver">
            <DriverDashboard />
          </ProtectedRoute>
        }
      />

      {/* Default — redirect to login */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <PreferencesProvider>
          <AppRoutes />
        </PreferencesProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
