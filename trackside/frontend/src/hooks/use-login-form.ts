/**
 * Trackside — Login Form State & Submission Hook.
 * Manages role switching, default demo identifiers, credentials state,
 * and session authentication submission.
 */

import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";

export type RoleType = "coach" | "admin" | "driver";

export const DEMO_IDENTIFIERS: Record<RoleType, string> = {
  admin: "admin@trackside.local",
  coach: "coach@trackside.local",
  driver: "driver@trackside.local",
};

export function useLoginForm() {
  const { login, error, clearError } = useAuth();
  const navigate = useNavigate();

  const [selectedRole, setSelectedRole] = useState<RoleType>("coach");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  /**
   * Updates the selected role tab and fills in corresponding demo identifier.
   */
  function handleRoleSelect(role: RoleType) {
    setSelectedRole(role);
    if (!identifier || Object.values(DEMO_IDENTIFIERS).includes(identifier)) {
      setIdentifier(DEMO_IDENTIFIERS[role]);
    }
  }

  /**
   * Submits user credentials to obtain a valid session cookie and navigates to the target dashboard.
   */
  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (isSubmitting) return;

    clearError();
    setIsSubmitting(true);

    const targetLoginId = identifier || DEMO_IDENTIFIERS[selectedRole];

    try {
      const authenticatedUser = await login(targetLoginId, password);
      navigate(`/${authenticatedUser.role}`, { replace: true });
    } catch {
      // Handled in auth context state
    } finally {
      setIsSubmitting(false);
    }
  }

  return {
    selectedRole,
    identifier,
    setIdentifier,
    password,
    setPassword,
    isSubmitting,
    error,
    handleRoleSelect,
    handleSubmit,
  };
}
