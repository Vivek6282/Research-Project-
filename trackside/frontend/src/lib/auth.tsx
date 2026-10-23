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
  useRef,
  type ReactNode,
} from "react";
import { api, fetchCSRFToken } from "./api";
import { clearPrivateCaches } from "./private-cache";

/** Do not ask the server who is signed in more often than this when the tab gains focus. */
export const SESSION_RECHECK_MIN_MS = 5000;
/** How often, and how far apart, the first read of the session is repeated when the server does not answer. */
export const SESSION_READ_RETRIES = 3;
export const SESSION_READ_RETRY_MS = 1500;

/** True when the server clearly refused the session (401 or 403), not when it was only slow or unreachable. */
function isSignedOut(err: unknown): boolean {
  const status = (err as { status?: number } | null)?.status;
  return status === 401 || status === 403;
}

/** User shape returned by the API */
export interface User {
  id: string;
  username?: string;
  driver_code?: string | null;
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
  /** Says why this tab changed account on its own (another tab signed in or out); null when nothing happened. */
  sessionNotice: string | null;
  dismissSessionNotice: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * Ask the server who is signed in. When the server is only slow or waking up (a network failure or a 5xx),
 * try again a few times instead of treating it as "signed out"; a clear refusal is answered at once.
 */
async function readCurrentUser(): Promise<User> {
  for (let attempt = 0; ; attempt++) {
    try {
      return await api.get<User>("/api/auth/me/");
    } catch (err) {
      if (isSignedOut(err) || attempt >= SESSION_READ_RETRIES) throw err;
      await new Promise((resolve) => setTimeout(resolve, SESSION_READ_RETRY_MS));
    }
  }
}

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
  const [sessionNotice, setSessionNotice] = useState<string | null>(null);
  // The person currently shown, readable inside the focus handler without re-attaching it every render
  const userRef = useRef<User | null>(null);
  useEffect(() => {
    userRef.current = user;
  }, [user]);

  /** Check for existing session on app load */
  useEffect(() => {
    async function checkSession() {
      clearPrivateCaches();
      try {
        await fetchCSRFToken();
        const currentUser = await readCurrentUser();
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

  // The session cookie is shared by every tab of this browser. If another tab signs in as someone else
  // (or signs out), this tab must follow the server at once instead of showing the old person's page.
  useEffect(() => {
    let lastCheck = Date.now();
    async function recheck() {
      if (document.hidden || Date.now() - lastCheck < SESSION_RECHECK_MIN_MS) return;
      lastCheck = Date.now();
      try {
        const serverUser = await api.get<User>("/api/auth/me/");
        const shown = userRef.current;
        if (shown && (shown.id !== serverUser.id || shown.role !== serverUser.role)) {
          setSessionNotice(`Another tab signed in as ${serverUser.name} (${serverUser.role}), so this tab switched to that account.`);
          setUser(serverUser);
        }
      } catch (err) {
        // Only a refusal from the server means "signed out"; a network failure leaves the page as it is.
        if (isSignedOut(err)) {
          if (userRef.current) setSessionNotice("You were signed out in another tab.");
          setUser(null);
        }
      }
    }
    document.addEventListener("visibilitychange", recheck);
    window.addEventListener("focus", recheck);
    return () => {
      document.removeEventListener("visibilitychange", recheck);
      window.removeEventListener("focus", recheck);
    };
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
      clearPrivateCaches();
    }
  }, []);

  const clearError = useCallback(() => setError(null), []);
  const dismissSessionNotice = useCallback(() => setSessionNotice(null), []);

  return (
    <AuthContext.Provider
      value={{ user, isLoading, error, login, logout, clearError, sessionNotice, dismissSessionNotice }}
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
