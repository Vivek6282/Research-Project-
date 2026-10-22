/**
 * Trackside Admin Dashboard — User Management Roster Component.
 * Supports dual responsive layouts: mobile card list (< md) and full desktop data
 * table (>= md) with inline name/email editing and account activation toggling.
 */

import { UserRecord } from "../types";
import { UserMobileCards } from "./user-mobile-cards";
import { UserDesktopTable } from "./user-desktop-table";

interface UserManagementTableProps {
  users: UserRecord[];
  currentUser: any;
  fetchError: string | null;
  setFetchError: (v: string | null) => void;
  editingUserId: string | null;
  setEditingUserId: (id: string | null) => void;
  editName: string;
  setEditName: (v: string) => void;
  editEmail: string;
  setEditEmail: (v: string) => void;
  editCode: string;
  setEditCode: (v: string) => void;
  editError: string;
  startEdit: (u: UserRecord) => void;
  handleSaveEdit: () => void;
  handleToggleDeactivate: (u: UserRecord) => void;
  onDelete: (u: UserRecord) => void;
}

export function UserManagementTable({
  users,
  currentUser,
  fetchError,
  setFetchError,
  editingUserId,
  setEditingUserId,
  editName,
  setEditName,
  editEmail,
  setEditEmail,
  editCode,
  setEditCode,
  editError,
  startEdit,
  handleSaveEdit,
  handleToggleDeactivate,
  onDelete,
}: UserManagementTableProps) {
  return (
    <div>
      {/* API Fetch Error Banner */}
      {fetchError && (
        <div className="mb-4 p-3 rounded text-xs font-mono bg-[#F2A93B]/15 border border-[#F2A93B]/40 text-[#F2A93B] flex items-center justify-between">
          <span>⚠️ {fetchError}</span>
          <button
            onClick={() => setFetchError(null)}
            className="text-[10px] underline cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Mobile Card-Based Layout (< md) */}
      <UserMobileCards
        users={users}
        currentUser={currentUser}
        fetchError={fetchError}
        editingUserId={editingUserId}
        setEditingUserId={setEditingUserId}
        editName={editName}
        setEditName={setEditName}
        editEmail={editEmail}
        setEditEmail={setEditEmail}
        editCode={editCode}
        setEditCode={setEditCode}
        editError={editError}
        startEdit={startEdit}
        handleSaveEdit={handleSaveEdit}
        handleToggleDeactivate={handleToggleDeactivate}
        onDelete={onDelete}
      />

      {/* Desktop Tabular View (>= md) */}
      <UserDesktopTable
        users={users}
        currentUser={currentUser}
        fetchError={fetchError}
        editingUserId={editingUserId}
        setEditingUserId={setEditingUserId}
        editName={editName}
        setEditName={setEditName}
        editEmail={editEmail}
        setEditEmail={setEditEmail}
        editCode={editCode}
        setEditCode={setEditCode}
        editError={editError}
        startEdit={startEdit}
        handleSaveEdit={handleSaveEdit}
        handleToggleDeactivate={handleToggleDeactivate}
        onDelete={onDelete}
      />
    </div>
  );
}
