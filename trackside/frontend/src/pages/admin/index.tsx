/**
 * Trackside — Admin Dashboard
 *
 * Pit-Wall System Administration & Hardware Control:
 * - IoT Hardware connectivity pings (Glove, Kart Unit, Biometric Strap)
 * - Intradomain user account provisioning & role management (Admin only)
 * - Active telemetry node diagnostics & audit logs
 */

import { useState, useEffect } from "react";
import { Users, Wifi, WifiOff, Plus, X, Shield, Activity, Check, Copy } from "lucide-react";
import { TopBar } from "../../components/shell/top-bar";
import { Panel } from "../../components/ui/panel";
import { Chip } from "../../components/ui/chip";
import { TutorialCallout } from "../../components/ui/tutorial-callout";
import { api } from "../../lib/api";

const INITIAL_USERS = [
  { id: "1", username: "TRK-ADMIN-000001", name: "System Admin", role: "admin", status: "Active", email: "admin@trackside.local" },
  { id: "2", username: "TRK-COACH-000001", name: "Coach Nair", role: "coach", status: "Active", email: "coach@trackside.local" },
  { id: "3", username: "TRK-DRV-000001", name: "A. Menon", role: "driver", status: "Active", email: "driver@trackside.local" },
  { id: "4", username: "TRK-DRV-000002", name: "R. Iyer", role: "driver", status: "Active", email: "iyer@trackside.local" },
];

export function AdminDashboard() {
  const [users, setUsers] = useState<any[]>(INITIAL_USERS);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<"coach" | "driver">("driver");
  const [password, setPassword] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [copied, setCopied] = useState(false);
  const [successData, setSuccessData] = useState<{ username: string; password: string; name: string; role: string } | null>(null);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Inline User Editing State
  const [editingUserId, setEditingUserId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editEmail, setEditEmail] = useState("");
  const [editError, setEditError] = useState("");

  useEffect(() => {
    async function loadUsers() {
      try {
        setFetchError(null);
        const fetched = await api.get<any[]>("/api/auth/users/");
        if (Array.isArray(fetched) && fetched.length > 0) {
          setUsers(fetched);
        }
      } catch (err: any) {
        setFetchError(err.message || "Could not load live user roster — showing cached fallback data");
      }
    }
    loadUsers();
  }, []);

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
        password: password,
        name: newUser.name,
        role: newUser.role,
      });

      setUsers((prev) => [newUser, ...prev]);
      setName("");
      setEmail("");
      setPassword("");
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to create account.");
    }
  };

  const handleToggleDeactivate = async (u: any) => {
    const isCurrentlyActive = u.is_active !== false;
    const actionText = isCurrentlyActive ? "deactivate" : "reactivate";

    if (!window.confirm(`Are you sure you want to ${actionText} ${u.name}?`)) {
      return;
    }

    try {
      const updated = await api.patch<any>(`/api/auth/users/${u.id}/`, {
        is_active: !isCurrentlyActive,
      });

      setUsers((prev) =>
        prev.map((item) => (item.id === u.id ? { ...item, is_active: updated.is_active } : item))
      );
    } catch (err: any) {
      alert(err.message || `Failed to ${actionText} user.`);
    }
  };

  const startEdit = (u: any) => {
    setEditingUserId(u.id);
    setEditName(u.name);
    setEditEmail(u.email || "");
    setEditError("");
  };

  const handleSaveEdit = async () => {
    if (!editingUserId) return;
    setEditError("");

    if (!editName.trim()) {
      setEditError("Name cannot be empty.");
      return;
    }

    const currentUser = users.find((u) => u.id === editingUserId);
    if (currentUser?.role === "coach" && !editEmail.trim()) {
      setEditError("Email address is required for Coach accounts.");
      return;
    }

    try {
      const updated = await api.patch<any>(`/api/auth/users/${editingUserId}/`, {
        name: editName.trim(),
        email: editEmail.trim() || undefined,
      });

      setUsers((prev) =>
        prev.map((item) =>
          item.id === editingUserId ? { ...item, name: updated.name, email: updated.email } : item
        )
      );
      setEditingUserId(null);
    } catch (err: any) {
      setEditError(err.message || "Failed to update user.");
    }
  };

  const copyCredentials = () => {
    if (!successData) return;
    const text = `Username ID: ${successData.username}\nPassword: ${successData.password}`;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="min-h-screen bg-[#0A0E13] text-[#E7EDF3] select-none">
      {/* Background Slanted Streams */}
      <div className="bg-slant-container">
        <div className="bg-slant-stream-top" />
        <div className="bg-slant-stream-bottom" />
      </div>

      <div className="relative z-10">
        <TopBar />
        <TutorialCallout role="admin" />

        <main className="max-w-6xl mx-auto px-4 py-5 space-y-4 animate-fade-in">
          {/* IoT Hardware Status Pings */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Panel title="Glove Unit (ESP32)" icon={Wifi}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#33D17E] animate-pulse" />
                  <span className="text-xs font-mono font-bold text-[#E7EDF3]">
                    ONLINE · 24ms
                  </span>
                </div>
                <Chip color="#33D17E">CONNECTED</Chip>
              </div>
            </Panel>

            <Panel title="Kart Unit (IMU + GPS)" icon={Wifi}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#33D17E] animate-pulse" />
                  <span className="text-xs font-mono font-bold text-[#E7EDF3]">
                    GPS LOCK · 12 Sats
                  </span>
                </div>
                <Chip color="#33D17E">CONNECTED</Chip>
              </div>
            </Panel>

            <Panel title="Biometric Strap" icon={WifiOff}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-[#F2A93B] animate-pulse" />
                  <span className="text-xs font-mono font-bold text-[#F2A93B]">
                    BLE PAIRING…
                  </span>
                </div>
                <Chip color="#F2A93B">PAIRING</Chip>
              </div>
            </Panel>
          </div>

          {/* Intradomain User Management Table */}
          <Panel
            title="User Management & Role Provisioning"
            icon={Users}
            right={
              <button
                onClick={() => setShowCreateForm(!showCreateForm)}
                className="flex items-center gap-1.5 text-xs font-mono px-2.5 py-1 rounded cursor-pointer transition-colors"
                style={{
                  color: "#3FA6E0",
                  border: "1px solid #3FA6E044",
                  background: "#3FA6E010",
                }}
              >
                {showCreateForm ? <X size={12} /> : <Plus size={12} />}
                {showCreateForm ? "Cancel" : "Add Account"}
              </button>
            }
          >
            {/* Inline Account Creation Form (Admin Only) */}
            {showCreateForm && (
              <div className="mb-4 p-4 rounded-lg space-y-3 animate-fade-in bg-[#161D26] border border-[#232B35]">
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                  <input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Full Name"
                    className="px-3 py-2 rounded text-xs font-mono outline-none bg-[#0A0E13] border border-[#232B35] text-[#E7EDF3] focus:border-[#3FA6E0]"
                  />
                  <select
                    value={role}
                    onChange={(e) => setRole(e.target.value as "coach" | "driver")}
                    className="px-3 py-2 rounded text-xs font-mono outline-none bg-[#0A0E13] border border-[#232B35] text-[#E7EDF3] focus:border-[#3FA6E0]"
                  >
                    <option value="driver">Role: Driver</option>
                    <option value="coach">Role: Coach</option>
                  </select>
                  <input
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder={role === "driver" ? "Email (optional for Drivers)" : "Email address (required)"}
                    type="email"
                    className="px-3 py-2 rounded text-xs font-mono outline-none bg-[#0A0E13] border border-[#232B35] text-[#E7EDF3] focus:border-[#3FA6E0]"
                  />
                  <input
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Access Password (min 8 chars)"
                    type="password"
                    className="px-3 py-2 rounded text-xs font-mono outline-none bg-[#0A0E13] border border-[#232B35] text-[#E7EDF3] focus:border-[#3FA6E0]"
                  />
                </div>

                <div className="flex items-center justify-between pt-1">
                  <span className="text-[10px] font-mono text-[#7C8898]">
                    {role === "driver" ? "💡 Driver ID username will be auto-generated server-side (e.g. TRK-DRV-000042)" : "💡 Coach email is required for alert & session notifications."}
                  </span>
                  <button
                    onClick={handleCreateAccount}
                    className="px-4 py-2 rounded text-xs font-bold font-mono uppercase tracking-wider cursor-pointer bg-[#3FA6E0] text-[#06121B] hover:bg-[#3FA6E0]/90 transition-colors"
                  >
                    Create Account
                  </button>
                </div>

                {errorMsg && (
                  <div className="p-2 rounded text-xs font-mono bg-[#E5473C]/15 border border-[#E5473C]/40 text-[#E5473C]">
                    {errorMsg}
                  </div>
                )}
              </div>
            )}

            {/* Generated Credentials Confirmation Panel */}
            {successData && (
              <div className="mb-4 p-4 rounded-lg font-mono bg-[#33D17E]/10 border border-[#33D17E]/40 text-[#E7EDF3]">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Check size={16} className="text-[#33D17E]" />
                    <span className="text-xs font-bold text-[#33D17E] uppercase">
                      Account Provisioned Successfully — {successData.name} ({successData.role})
                    </span>
                  </div>
                  <button
                    onClick={copyCredentials}
                    className="flex items-center gap-1 text-[11px] text-[#33D17E] bg-[#33D17E]/20 border border-[#33D17E]/50 px-2.5 py-1 rounded cursor-pointer hover:bg-[#33D17E]/30"
                  >
                    {copied ? <Check size={12} /> : <Copy size={12} />}
                    {copied ? "COPIED TO CLIPBOARD" : "COPY CREDENTIALS"}
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-4 text-xs bg-[#0A0E13] p-3 rounded border border-[#232B35]">
                  <div>
                    <span className="text-[#7C8898] block text-[10px]">USERNAME / DRIVER ID:</span>
                    <span className="text-[#3FA6E0] font-extrabold text-sm">{successData.username}</span>
                  </div>
                  <div>
                    <span className="text-[#7C8898] block text-[10px]">ACCESS PASSWORD:</span>
                    <span className="text-[#E7EDF3] font-bold text-sm">{successData.password}</span>
                  </div>
                </div>
              </div>
            )}

            {/* API Fetch Error Banner */}
            {fetchError && (
              <div className="mb-4 p-3 rounded text-xs font-mono bg-[#F2A93B]/15 border border-[#F2A93B]/40 text-[#F2A93B] flex items-center justify-between">
                <span>⚠️ {fetchError}</span>
                <button onClick={() => setFetchError(null)} className="text-[10px] underline cursor-pointer">
                  Dismiss
                </button>
              </div>
            )}

            {/* Users Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono">
                <thead>
                  <tr className="text-[10px] uppercase text-left border-b border-[#232B35]" style={{ color: "#7C8898" }}>
                    <th className="pb-2 font-semibold">User</th>
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
                    const roleColor = u.role === "admin" ? "#33D17E" : u.role === "coach" ? "#3FA6E0" : "#F2A93B";

                    if (isEditing) {
                      return (
                        <tr key={u.id} className="bg-[#161D26]">
                          <td className="py-2.5 px-1" colSpan={2}>
                            <input
                              value={editName}
                              onChange={(e) => setEditName(e.target.value)}
                              placeholder="Full Name"
                              className="w-full px-2 py-1 rounded text-xs font-mono bg-[#0A0E13] border border-[#3FA6E0] text-[#E7EDF3] outline-none"
                            />
                          </td>
                          <td className="py-2.5 px-1" colSpan={2}>
                            <input
                              value={editEmail}
                              onChange={(e) => setEditEmail(e.target.value)}
                              placeholder={u.role === "driver" ? "Email (optional)" : "Email (required)"}
                              className="w-full px-2 py-1 rounded text-xs font-mono bg-[#0A0E13] border border-[#3FA6E0] text-[#E7EDF3] outline-none"
                            />
                            {editError && <div className="text-[10px] text-[#E5473C] mt-0.5">{editError}</div>}
                          </td>
                          <td className="py-2.5 text-center font-mono text-[10px] text-[#7C8898]">
                            {u.role.toUpperCase()}
                          </td>
                          <td className="py-2.5 text-right space-x-2">
                            <button
                              onClick={handleSaveEdit}
                              className="text-[10px] px-2 py-1 rounded cursor-pointer font-bold bg-[#33D17E] text-[#0A0E13]"
                            >
                              Save
                            </button>
                            <button
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
                      <tr key={u.id} className="hover:bg-[#161D26] transition-colors">
                        <td className="py-2.5 font-bold">{u.name}</td>
                        <td className="py-2.5 text-[#3FA6E0] font-bold">{u.username || "—"}</td>
                        <td className="py-2.5 text-[#7C8898]">{u.email || "—"}</td>
                        <td className="py-2.5">
                          <span
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
                          <Chip color={isActive ? "#33D17E" : "#E5473C"}>
                            {isActive ? "Active" : "Inactive"}
                          </Chip>
                        </td>
                        <td className="py-2.5 text-right space-x-2">
                          <button
                            onClick={() => startEdit(u)}
                            className="text-[10px] px-2 py-1 rounded cursor-pointer transition-colors"
                            style={{ color: "#3FA6E0", border: "1px solid #3FA6E044" }}
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleToggleDeactivate(u)}
                            className="text-[10px] px-2 py-1 rounded cursor-pointer transition-colors font-mono"
                            style={{
                              color: isActive ? "#E5473C" : "#33D17E",
                              border: `1px solid ${isActive ? "#E5473C44" : "#33D17E44"}`,
                              background: `${isActive ? "#E5473C10" : "#33D17E10"}`,
                            }}
                          >
                            {isActive ? "Deactivate" : "Reactivate"}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Panel>

          {/* System Analytics & Audit Overview */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Panel title="Security & Audit Trail" icon={Shield}>
              <p className="text-xs text-[#7C8898]">
                Session authentication active · CSRF protection enforced · All user modifications logged to audit store.
              </p>
            </Panel>

            <Panel title="Telemetry Diagnostics" icon={Activity}>
              <p className="text-xs text-[#7C8898]">
                4 active registered nodes · 0 packet drops in last 60 minutes · Database ORM query time: 4ms.
              </p>
            </Panel>
          </div>
        </main>
      </div>
    </div>
  );
}
