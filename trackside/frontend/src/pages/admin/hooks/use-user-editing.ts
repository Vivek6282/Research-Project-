/**
 * Trackside Admin Dashboard — Inline User Editing Hook.
 * Holds the edit fields (name, email, driver ID) of the row being edited and saves them
 * with PATCH /api/auth/users/<id>/. A server error is shown in the row (editError).
 */

import { useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { api } from "../../../lib/api";
import { UserRecord } from "../types";

export function useUserEditing(
  users: UserRecord[],
  setUsers: Dispatch<SetStateAction<UserRecord[]>>,
  onSaved: () => void,
) {
  const [editingUserId, setEditingUserId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editEmail, setEditEmail] = useState("");
  const [editCode, setEditCode] = useState("");
  const [editError, setEditError] = useState("");

  // Open the edit fields for one user
  const startEdit = (u: UserRecord) => {
    setEditingUserId(u.id);
    setEditName(u.name);
    setEditEmail(u.email || "");
    setEditCode(u.driver_code || "");
    setEditError("");
  };

  // Check the fields, send the changes and update the row
  const handleSaveEdit = async () => {
    if (!editingUserId) return;
    setEditError("");

    if (!editName.trim()) {
      setEditError("Name cannot be empty.");
      return;
    }

    const target = users.find((u) => u.id === editingUserId);
    if (target?.role === "coach" && !editEmail.trim()) {
      setEditError("Email address is required for Coach accounts.");
      return;
    }

    try {
      const updated = await api.patch<any>(`/api/auth/users/${editingUserId}/`, {
        name: editName.trim(),
        email: editEmail.trim() || undefined,
        ...(target?.role === "driver" && editCode.trim() ? { driver_code: editCode.trim().toUpperCase() } : {}),
      });

      setUsers((prev) =>
        prev.map((item) =>
          item.id === editingUserId
            ? { ...item, name: updated.name, email: updated.email, driver_code: updated.driver_code }
            : item
        )
      );
      setEditingUserId(null);
      onSaved();
    } catch (err: any) {
      setEditError(err.message || "Failed to update user.");
    }
  };

  return {
    editingUserId, setEditingUserId, editName, setEditName, editEmail, setEditEmail,
    editCode, setEditCode, editError, startEdit, handleSaveEdit,
  };
}
