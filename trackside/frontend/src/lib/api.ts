/**
 * Trackside — API Client
 *
 * Centralized fetch wrapper that handles:
 * - CSRF tokens (double-submit pattern for Django session auth)
 * - Credentials inclusion (cookies sent with every request)
 * - Consistent error handling (401 → redirect, 403 → role error)
 *
 * All API calls go through this module — never use raw fetch().
 */

/** Read the CSRF token from the cookie set by Django */
function getCSRFToken(): string {
  const cookies = document.cookie.split(";");
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split("=");
    if (name === "csrftoken") {
      return decodeURIComponent(value);
    }
  }
  return "";
}

/** Base configuration for all API requests */
interface RequestConfig extends Omit<RequestInit, "body"> {
  body?: unknown;
}

/**
 * Core fetch wrapper — handles CSRF, credentials, and error responses.
 * Returns the parsed JSON response or throws an error.
 */
async function request<T>(url: string, config: RequestConfig = {}): Promise<T> {
  const { body, headers: customHeaders, ...rest } = config;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(customHeaders as Record<string, string>),
  };

  // Include CSRF token for state-changing requests
  const method = (rest.method || "GET").toUpperCase();
  if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    headers["X-CSRFToken"] = getCSRFToken();
  }

  const response = await fetch(url, {
    ...rest,
    headers,
    credentials: "include", // Always send session cookie
    body: body ? JSON.stringify(body) : undefined,
  });

  // Handle common error codes
  if (response.status === 401) {
    // Session expired or not authenticated — redirect to login
    window.location.href = "/login";
    throw new Error("Authentication required");
  }

  if (response.status === 429) {
    throw new Error("Too many requests. Please wait and try again.");
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const message =
      errorData.detail ||
      errorData.message ||
      `Request failed with status ${response.status}`;
    throw new Error(message);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

/** Convenience methods for common HTTP verbs */
export const api = {
  get: <T>(url: string) => request<T>(url),

  post: <T>(url: string, body?: unknown) =>
    request<T>(url, { method: "POST", body }),

  put: <T>(url: string, body?: unknown) =>
    request<T>(url, { method: "PUT", body }),

  patch: <T>(url: string, body?: unknown) =>
    request<T>(url, { method: "PATCH", body }),

  delete: <T>(url: string) => request<T>(url, { method: "DELETE" }),
};

/**
 * Fetch the CSRF token from Django before any state-changing request.
 * Should be called once when the app loads.
 */
export async function fetchCSRFToken(): Promise<void> {
  await fetch("/api/auth/csrf/", { credentials: "include" });
}
