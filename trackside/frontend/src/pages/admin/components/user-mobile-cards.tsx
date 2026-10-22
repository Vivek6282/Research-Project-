/**
 * Trackside Admin Dashboard — Mobile User Cards Component.
 * Responsive card layout for screens < md with inline editing and deactivation.
 */

import { Chip } from "../../../components/ui/chip";
import { UserRecord } from "../types";

interface UserMobileCardsProps {
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

export function UserMobileCards({
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
}: UserMobileCardsProps) {
  return (
    <div data-testid="admin-user-cards-container" className="block md:hidden space-y-3 font-mono">
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
            <div
              key={`card-${u.id}`}
              data-testid="admin-user-card"
              className="bg-[#161D26] border border-[#3FA6E0] p-3.5 rounded-lg space-y-2.5"
            >
              <div className="text-xs font-bold text-[#3FA6E0]">EDITING USER</div>
              <div>
                <label className="text-[10px] text-[#7C8898] block mb-1">FULL NAME</label>
                <input
                  data-testid="admin-edit-name-input"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  placeholder="Full Name"
                  className="w-full px-3 py-2 rounded text-xs bg-[#0A0E13] border border-[#3FA6E0] text-[#E7EDF3] outline-none"
                />
              </div>
              {u.role === "driver" && (
                <div>
                  <label className="text-[10px] text-[#7C8898] block mb-1">DRIVER ID</label>
                  <input
                    data-testid="admin-edit-code-input"
                    value={editCode}
                    onChange={(e) => setEditCode(e.target.value)}
                    placeholder="D17256"
                    maxLength={6}
                    className="w-full px-3 py-2 rounded text-xs bg-[#0A0E13] border border-[#3FA6E0] text-[#E7EDF3] outline-none"
                  />
                </div>
              )}
              <div>
                <label className="text-[10px] text-[#7C8898] block mb-1">EMAIL ADDRESS</label>
                <input
                  data-testid="admin-edit-email-input"
                  value={editEmail}
                  onChange={(e) => setEditEmail(e.target.value)}
                  placeholder={u.role === "driver" ? "Email (optional)" : "Email (required)"}
                  className="w-full px-3 py-2 rounded text-xs bg-[#0A0E13] border border-[#3FA6E0] text-[#E7EDF3] outline-none"
                />
                {editError && (
                  <div data-testid="admin-edit-error" className="text-[10px] text-[#E5473C] mt-1">
                    {editError}
                  </div>
                )}
              </div>
              <div className="flex gap-2 pt-1">
                <button
                  data-testid="admin-edit-save-btn"
                  onClick={handleSaveEdit}
                  className="flex-1 py-2 rounded font-bold text-xs bg-[#33D17E] text-[#0A0E13] min-h-[40px] cursor-pointer"
                >
                  Save Changes
                </button>
                <button
                  data-testid="admin-edit-cancel-btn"
                  onClick={() => setEditingUserId(null)}
                  className="px-4 py-2 rounded text-xs text-[#7C8898] border border-[#232B35] bg-[#0A0E13] min-h-[40px] cursor-pointer"
                >
                  Cancel
                </button>
              </div>
            </div>
          );
        }

        return (
          <div
            key={`card-${u.id}`}
            data-testid="admin-user-card"
            className="bg-[#161D26] border border-[#232B35] p-3.5 rounded-lg space-y-2.5 hover:border-[#3A4553] transition-colors"
          >
            <div className="flex items-start justify-between">
              <div>
                <div data-testid={`admin-user-name-${u.id}`} className="font-bold text-sm text-[#E7EDF3]">
                  {u.name}
                </div>
                <div data-testid={`admin-user-username-${u.id}`} className="text-xs text-[#3FA6E0] font-bold">
                  {u.username || "—"}
                </div>
                <div data-testid={`admin-user-code-${u.id}`} className="text-xs text-[#F2A93B] font-bold">
                  ID {u.driver_code || "-"}
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <span
                  data-testid={`admin-user-role-${u.id}`}
                  className="px-2 py-0.5 rounded text-[10px] uppercase font-bold"
                  style={{
                    color: roleColor,
                    border: `1px solid ${roleColor}44`,
                    background: `${roleColor}10`,
                  }}
                >
                  {u.role}
                </span>
                <span data-testid={`admin-user-status-${u.id}`}>
                  <Chip color={isActive ? "#33D17E" : "#E5473C"}>
                    {isActive ? "Active" : "Inactive"}
                  </Chip>
                </span>
              </div>
            </div>

            <div className="text-xs text-[#7C8898] border-t border-[#232B35]/60 pt-2 flex items-center justify-between">
              <span data-testid={`admin-user-email-${u.id}`} className="truncate max-w-[200px]">
                {u.email || "No email assigned"}
              </span>
            </div>

            <div className="flex gap-2 pt-1 border-t border-[#232B35]/60">
              <button
                data-testid={`admin-user-edit-btn-${u.id}`}
                disabled={!!fetchError}
                onClick={() => startEdit(u)}
                className={`flex-1 py-2 min-h-[40px] rounded text-xs font-bold transition-colors ${
                  fetchError ? "opacity-40 cursor-not-allowed" : "cursor-pointer hover:bg-[#3FA6E0]/10"
                }`}
                style={{ color: "#3FA6E0", border: "1px solid #3FA6E044", background: "#3FA6E010" }}
              >
                Edit
              </button>
              <button
                data-testid={`admin-user-deactivate-btn-${u.id}`}
                disabled={!!fetchError || isSelfDeactivating}
                onClick={() => handleToggleDeactivate(u)}
                className={`flex-1 py-2 min-h-[40px] rounded text-xs font-bold transition-colors font-mono ${
                  fetchError || isSelfDeactivating ? "opacity-40 cursor-not-allowed" : "cursor-pointer"
                }`}
                style={{
                  color: isActive ? "#E5473C" : "#33D17E",
                  border: `1px solid ${isActive ? "#E5473C44" : "#33D17E44"}`,
                  background: `${isActive ? "#E5473C10" : "#33D17E10"}`,
                }}
              >
                {isActive ? "Deactivate" : "Reactivate"}
              </button>
              <button
                data-testid="admin-delete-btn"
                disabled={!!fetchError || !!isSelf || u.role === "admin"}
                onClick={() => onDelete(u)}
                className={`flex-1 py-2 min-h-[40px] rounded text-xs font-bold transition-colors font-mono ${
                  fetchError || isSelf || u.role === "admin" ? "opacity-40 cursor-not-allowed" : "cursor-pointer"
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
            </div>
          </div>
        );
      })}
    </div>
  );
}
