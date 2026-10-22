/**
 * Trackside Admin Dashboard — Desktop User Table Component.
 * Responsive data table layout for screens >= md with inline row editing and deactivation.
 */

import { Chip } from "../../../components/ui/chip";
import { UserRecord } from "../types";

interface UserDesktopTableProps {
  users: UserRecord[];
  currentUser: any;
  fetchError: string | null;
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

export function UserDesktopTable({
  users,
  currentUser,
  fetchError,
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
}: UserDesktopTableProps) {
  return (
    <div className="hidden md:block overflow-x-auto">
      <table data-testid="admin-user-table" className="w-full text-xs font-mono">
        <thead>
          <tr className="text-[10px] uppercase text-left border-b border-[#232B35]" style={{ color: "#7C8898" }}>
            <th className="pb-2 font-semibold">User</th>
            <th className="pb-2 font-semibold">ID</th>
            <th className="pb-2 font-semibold">Username ID</th>
            <th className="pb-2 font-semibold">Email</th>
            <th className="pb-2 font-semibold">Role</th>
            <th className="pb-2 font-semibold">Status</th>
            <th className="pb-2 text-right font-semibold">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[#232B35]">
          {users.map((u) => {
            const isEditing = editingUserId === u.id;
            const isActive = u.is_active !== false && u.status !== "Inactive";
            const isSelf =
              currentUser &&
              (currentUser.id === u.id ||
                (currentUser.email && u.email && currentUser.email === u.email));
            const isSelfDeactivating = isSelf && isActive;
            const roleColor =
              u.role === "admin" ? "#33D17E" : u.role === "coach" ? "#3FA6E0" : "#F2A93B";

            if (isEditing) {
              return (
                <tr key={`tbl-${u.id}`} data-testid="admin-user-row" data-user-id={u.id} className="bg-[#161D26]">
                  <td className="py-2.5 px-1">
                    <input
                      data-testid="admin-edit-name-input"
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      placeholder="Full Name"
                      className="w-full px-2 py-1 rounded text-xs font-mono bg-[#0A0E13] border border-[#3FA6E0] text-[#E7EDF3] outline-none"
                    />
                  </td>
                  <td className="py-2.5 px-1">
                    {u.role === "driver" ? (
                      <input
                        data-testid="admin-edit-code-input"
                        value={editCode}
                        onChange={(e) => setEditCode(e.target.value)}
                        placeholder="D17256"
                        maxLength={6}
                        className="w-full px-2 py-1 rounded text-xs font-mono bg-[#0A0E13] border border-[#3FA6E0] text-[#E7EDF3] outline-none"
                      />
                    ) : (
                      <span className="text-[#F2A93B] font-bold">-</span>
                    )}
                  </td>
                  <td className="py-2.5 px-1 text-[#3FA6E0] font-bold">{u.username || "—"}</td>
                  <td className="py-2.5 px-1" colSpan={2}>
                    <input
                      data-testid="admin-edit-email-input"
                      value={editEmail}
                      onChange={(e) => setEditEmail(e.target.value)}
                      placeholder={u.role === "driver" ? "Email (optional)" : "Email (required)"}
                      className="w-full px-2 py-1 rounded text-xs font-mono bg-[#0A0E13] border border-[#3FA6E0] text-[#E7EDF3] outline-none"
                    />
                    {editError && (
                      <div data-testid="admin-edit-error" className="text-[10px] text-[#E5473C] mt-0.5">
                        {editError}
                      </div>
                    )}
                  </td>
                  <td className="py-2.5 text-center font-mono text-[10px] text-[#7C8898]">
                    {u.role.toUpperCase()}
                  </td>
                  <td className="py-2.5 text-right space-x-2">
                    <button
                      data-testid="admin-edit-save-btn"
                      onClick={handleSaveEdit}
                      className="text-[10px] px-2 py-1 rounded cursor-pointer font-bold bg-[#33D17E] text-[#0A0E13]"
                    >
                      Save
                    </button>
                    <button
                      data-testid="admin-edit-cancel-btn"
                      onClick={() => setEditingUserId(null)}
                      className="text-[10px] px-2 py-1 rounded cursor-pointer text-[#7C8898] border border-[#232B35]"
                    >
                      Cancel
                    </button>
                  </td>
                </tr>
              );
            }

            return (
              <tr key={`tbl-${u.id}`} data-testid="admin-user-row" data-user-id={u.id} className="hover:bg-[#161D26] transition-colors">
                <td data-testid={`admin-user-name-${u.id}`} className="py-2.5 font-bold">
                  {u.name}
                </td>
                <td data-testid={`admin-user-code-${u.id}`} className="py-2.5 text-[#F2A93B] font-bold">
                  {u.driver_code || "-"}
                </td>
                <td data-testid={`admin-user-username-${u.id}`} className="py-2.5 text-[#3FA6E0] font-bold">
                  {u.username || "—"}
                </td>
                <td data-testid={`admin-user-email-${u.id}`} className="py-2.5 text-[#7C8898]">
                  {u.email || "—"}
                </td>
                <td className="py-2.5">
                  <span
                    data-testid={`admin-user-role-${u.id}`}
                    className="px-1.5 py-0.5 rounded text-[10px] uppercase font-bold"
                    style={{
                      color: roleColor,
                      border: `1px solid ${roleColor}44`,
                      background: `${roleColor}10`,
                    }}
                  >
                    {u.role}
                  </span>
                </td>
                <td className="py-2.5">
                  <span data-testid={`admin-user-status-${u.id}`}>
                    <Chip color={isActive ? "#33D17E" : "#E5473C"}>
                      {isActive ? "Active" : "Inactive"}
                    </Chip>
                  </span>
                </td>
                <td className="py-2.5 text-right space-x-2">
                  <button
                    data-testid={`admin-user-edit-btn-${u.id}`}
                    disabled={!!fetchError}
                    onClick={() => startEdit(u)}
                    className={`text-[10px] px-2.5 py-1.5 rounded transition-colors ${
                      fetchError ? "opacity-40 cursor-not-allowed" : "cursor-pointer hover:bg-[#3FA6E0]/10"
                    }`}
                    style={{ color: "#3FA6E0", border: "1px solid #3FA6E044" }}
                    title={fetchError ? "Actions disabled while user roster fetch fails" : "Edit user"}
                  >
                    Edit
                  </button>
                  <button
                    data-testid={`admin-user-deactivate-btn-${u.id}`}
                    disabled={!!fetchError || isSelfDeactivating}
                    onClick={() => handleToggleDeactivate(u)}
                    className={`text-[10px] px-2.5 py-1.5 rounded transition-colors font-mono ${
                      fetchError || isSelfDeactivating ? "opacity-40 cursor-not-allowed" : "cursor-pointer"
                    }`}
                    style={{
                      color: isActive ? "#E5473C" : "#33D17E",
                      border: `1px solid ${isActive ? "#E5473C44" : "#33D17E44"}`,
                      background: `${isActive ? "#E5473C10" : "#33D17E10"}`,
                    }}
                    title={
                      fetchError
                        ? "Actions disabled while user roster fetch fails"
                        : isSelfDeactivating
                        ? "You cannot deactivate your own admin account"
                        : isActive
                        ? "Deactivate user"
                        : "Reactivate user"
                    }
                  >
                    {isActive ? "Deactivate" : "Reactivate"}
                  </button>
                  <button
                    data-testid="admin-delete-btn"
                    disabled={!!fetchError || !!isSelf || u.role === "admin"}
                    onClick={() => onDelete(u)}
                    className={`text-[10px] px-2.5 py-1.5 rounded transition-colors font-mono ${
                      fetchError || isSelf || u.role === "admin" ? "opacity-40 cursor-not-allowed" : "cursor-pointer hover:bg-[#E5473C]/10"
                    }`}
                    style={{ color: "#E5473C", border: "1px solid #E5473C" }}
                    title={
                      isSelf
                        ? "You cannot delete your own account"
                        : u.role === "admin"
                        ? "Admin accounts cannot be deleted"
                        : "Delete user permanently"
                    }
                  >
                    Delete
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
