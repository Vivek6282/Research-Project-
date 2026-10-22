/**
 * Trackside Admin Dashboard — State & Mutation Hook.
 * Manages user rosters, device hardware queries, user creation/editing/deactivation,
 * clipboard copy, and audit trail/diagnostics polling.
 */

import { useState, useEffect, useCallback } from "react";
import { api } from "../../../lib/api";
import { useUserEditing } from "./use-user-editing";
import { useUserDelete } from "./use-user-delete";
import {
  UserRecord,
  DeviceRecord,
  AuditEntry,
  DiagnosticsData,
  SuccessData,
  ConfirmModalState,
} from "../types";

const INITIAL_USERS: UserRecord[] = [
  { id: "1", username: "TRK-ADMIN-000001", name: "System Admin", role: "admin", status: "Active", email: "admin@trackside.local" },
  { id: "2", username: "TRK-COACH-000001", name: "Coach Nair", role: "coach", status: "Active", email: "coach@trackside.local" },
  { id: "3", username: "TRK-DRV-000001", name: "A. Menon", role: "driver", status: "Active", email: "driver@trackside.local" },
  { id: "4", username: "TRK-DRV-000002", name: "R. Iyer", role: "driver", status: "Active", email: "iyer@trackside.local" },
];

export function useAdminDashboard() {
  const [users, setUsers] = useState<UserRecord[]>(INITIAL_USERS);
  const [devices, setDevices] = useState<DeviceRecord[]>([]);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Form states
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<"coach" | "driver">("driver");
  const [password, setPassword] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [copied, setCopied] = useState(false);
  const [successData, setSuccessData] = useState<SuccessData | null>(null);

  // Confirmation modal
  const [confirmModal, setConfirmModal] = useState<ConfirmModalState>({
    isOpen: false,
    title: "",
    message: "",
    userToToggle: null,
    isCurrentlyActive: true,
  });

  // Diagnostics & audit
  const [auditLogs, setAuditLogs] = useState<AuditEntry[]>([]);
  const [audit30DayCount, setAudit30DayCount] = useState<number>(0);
  const [diagnostics, setDiagnostics] = useState<DiagnosticsData | null>(null);

  const fetchAuditAndDiagnostics = useCallback(async () => {
    try {
      const auditRes: any = await api.get("/api/auth/audit-logs/");
      if (auditRes) {
        setAudit30DayCount(auditRes.count_30_days || 0);
        setAuditLogs(Array.isArray(auditRes.results) ? auditRes.results : []);
      }
    } catch (err) {
      console.warn("[useAdminDashboard] audit logs fetch error:", err);
    }

    try {
      const diagRes: any = await api.get("/api/auth/diagnostics/");
      if (diagRes) {
        setDiagnostics(diagRes);
      }
    } catch (err) {
      console.warn("[useAdminDashboard] diagnostics fetch error:", err);
    }
  }, []);

  const editing = useUserEditing(users, setUsers, fetchAuditAndDiagnostics);

  const refreshDevices = useCallback(async () => {
    try {
      const fetched: any = await api.get("/api/devices/");
      setDevices(Array.isArray(fetched) ? fetched : fetched?.results || []);
    } catch (err) {
      console.error("[useAdminDashboard] loadDevices failure:", err);
    }
  }, []);

  useEffect(() => {
    async function loadUsers() {
      try {
        setFetchError(null);
        const fetched: any = await api.get("/api/auth/users/");
        const userList = Array.isArray(fetched)
          ? fetched
          : Array.isArray(fetched?.results)
          ? fetched.results
          : [];
        setUsers(userList);
      } catch (err: any) {
        console.error("[useAdminDashboard] loadUsers failure:", err);
        setFetchError(
          err.message || "Could not load live user roster — showing cached fallback data"
        );
      }
    }
    loadUsers();
    refreshDevices();
    fetchAuditAndDiagnostics();
  }, [fetchAuditAndDiagnostics, refreshDevices]);

  const handleCreateAccount = async () => {
    setErrorMsg("");
    setSuccessData(null);

    if (!name.trim()) {
      setErrorMsg("Full Name is required.");
      return;
    }
    if (role === "coach" && !email.trim()) {
      setErrorMsg("Email address is required for Coach accounts.");
      return;
    }
    if (!password || password.length < 8) {
      setErrorMsg("Password must be at least 8 characters long.");
      return;
    }

    try {
      const newUser = await api.post<any>("/api/auth/users/", {
        name: name.trim(),
        email: email.trim() || undefined,
        role,
        password,
      });

      setSuccessData({
        username: newUser.username,
        driver_code: newUser.driver_code,
        password: password,
        name: newUser.name,
        role: newUser.role,
      });

      setUsers((prev) => [newUser, ...prev]);
      setName("");
      setEmail("");
      setPassword("");
      fetchAuditAndDiagnostics();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to create account.");
    }
  };

  const handleToggleDeactivate = (u: UserRecord) => {
    const isCurrentlyActive = u.is_active !== false && u.status !== "Inactive";
    const actionText = isCurrentlyActive ? "deactivate" : "reactivate";

    setConfirmModal({
      isOpen: true,
      title: isCurrentlyActive ? "Deactivate User Account" : "Reactivate User Account",
      message: `Are you sure you want to ${actionText} ${u.name}? ${
        isCurrentlyActive
          ? "This user will no longer be able to log in to the Pit-Wall dashboard."
          : "This user will regain access to log in to the Pit-Wall dashboard."
      }`,
      userToToggle: u,
      isCurrentlyActive,
    });
  };

  const deletion = useUserDelete(setUsers, fetchAuditAndDiagnostics, handleToggleDeactivate);

  const executeToggleDeactivate = async () => {
    if (!confirmModal.userToToggle) return;
    const u = confirmModal.userToToggle;
    const isCurrentlyActive = confirmModal.isCurrentlyActive;
    const actionText = isCurrentlyActive ? "deactivate" : "reactivate";

    setConfirmModal((prev) => ({ ...prev, isOpen: false }));

    try {
      const updated = await api.patch<any>(`/api/auth/users/${u.id}/`, {
        is_active: !isCurrentlyActive,
      });

      setUsers((prev) =>
        prev.map((item) =>
          item.id === u.id
            ? { ...item, is_active: updated.is_active, status: updated.is_active ? "Active" : "Inactive" }
            : item
        )
      );
      fetchAuditAndDiagnostics();
    } catch (err: any) {
      alert(err.message || `Failed to ${actionText} user.`);
    }
  };

  const copyCredentials = () => {
    if (!successData) return;
    const text = `Username ID: ${successData.username}\nPassword: ${successData.password}`;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return {
    users,
    devices,
    refreshDevices,
    fetchError,
    setFetchError,
    showCreateForm,
    setShowCreateForm,
    name,
    setName,
    email,
    setEmail,
    role,
    setRole,
    password,
    setPassword,
    errorMsg,
    copied,
    successData,
    handleCreateAccount,
    copyCredentials,
    ...editing,
    ...deletion,
    confirmModal,
    setConfirmModal,
    handleToggleDeactivate,
    executeToggleDeactivate,
    auditLogs,
    audit30DayCount,
    diagnostics,
  };
}
