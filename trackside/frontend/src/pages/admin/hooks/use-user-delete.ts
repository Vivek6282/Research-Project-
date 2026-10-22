/**
 * Trackside Admin Dashboard — Permanent Delete Hook.
 * Tracks which user the delete dialog is open for and the notice shown after a delete.
 */

import { useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { UserRecord } from "../types";

export function useUserDelete(
  setUsers: Dispatch<SetStateAction<UserRecord[]>>,
  onChanged: () => void,
  deactivate: (user: UserRecord) => void,
) {
  const [userToDelete, setUserToDelete] = useState<UserRecord | null>(null);
  const [deleteNotice, setDeleteNotice] = useState("");

  // Open the dialog for one user
  const openDelete = (user: UserRecord) => {
    setDeleteNotice("");
    setUserToDelete(user);
  };

  // Close the dialog without deleting
  const closeDelete = () => setUserToDelete(null);

  // After a successful delete: close, remove the row and say what happened
  const handleDeleted = (user: UserRecord) => {
    setUsers((prev) => prev.filter((item) => item.id !== user.id));
    setUserToDelete(null);
    setDeleteNotice(`${user.name} (${user.driver_code || user.username || "-"}) was deleted permanently.`);
    onChanged();
  };

  // Close the dialog and use the existing deactivate flow instead
  const deactivateInstead = (user: UserRecord) => {
    setUserToDelete(null);
    deactivate(user);
  };

  return { userToDelete, deleteNotice, setDeleteNotice, openDelete, closeDelete, handleDeleted, deactivateInstead };
}
