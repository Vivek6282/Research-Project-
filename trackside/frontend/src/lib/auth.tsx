/**
 * Trackside — Auth Context & Guards
 *
 * Provides authentication state to the entire app via React Context.
 * On mount, checks if the user has an active session via /api/auth/me/.
 * Exposes login/logout functions and a RoleGuard component.
 *
 * NOTE: RoleGuard is for UX only — every API endpoint independently
 * checks the user's role server-side (requirement #4).
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { api, fetchCSRFToken } from "./api";

/** User shape returned by the API */
export interface User {
  id: string;
  username?: string;
  email?: string;
  name: string;
  role: "admin" | "coach" | "driver";
  is_active: boolean;
  created_at: string;
}

/** Auth context shape */
interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  error: string | null;
  login: (identifier: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * AuthProvider — wraps the app and manages authentication state.
 *
 * On mount, fetches a CSRF token and checks for an existing session.
 * Login creates a session, logout destroys it.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /** Check for existing session on app load */
  useEffect(() => {
    async function checkSession() {
      try {
        await fetchCSRFToken();
        const currentUser = await api.get<User>("/api/auth/me/");
        setUser(currentUser);
      } catch {
        // No active session — user needs to log in
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    }
    checkSession();
  }, []);

  /** Log in with email or username and password */
  const login = useCallback(async (identifier: string, password: string) => {
    setError(null);
    try {
      await fetchCSRFToken();
      const loggedInUser = await api.post<User>("/api/auth/login/", {
        identifier,
        email: identifier,
        password,
      });
      setUser(loggedInUser);
      return loggedInUser;
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Login failed";
      setError(message);
      throw err;
    }
  }, []);

  /** Log out — destroys the session */
  const logout = useCallback(async () => {
    try {
      await api.post("/api/auth/logout/");
    } finally {
      setUser(null);
    }
  }, []);

  const clearError = useCallback(() => setError(null), []);

  return (
    <AuthContext.Provider
      value={{ user, isLoading, error, login, logout, clearError }}
    >
      {children}
    </AuthContext.Provider>
  );
}

/**
 * Hook to access auth state from any component.
 * Must be used within an AuthProvider.
 */
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

/**
 * RoleGuard — renders children only if the user has the required role.
 *
 * This is a UX convenience only — the server independently enforces
 * role-based access on every API call (requirement #4).
 */
export function RoleGuard({
  role,
  children,
  fallback,
}: {
  role: string | string[];
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const { user } = useAuth();
  const roles = Array.isArray(role) ? role : [role];

  if (!user || !roles.includes(user.role)) {
    return fallback || null;
  }

  return <>{children}</>;
}
