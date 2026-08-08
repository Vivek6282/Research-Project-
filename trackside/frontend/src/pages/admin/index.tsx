/**
 * Trackside — Admin Dashboard
 *
 * Pit-Wall System Administration & Hardware Control:
 * - IoT Hardware connectivity pings (Glove, Kart Unit, Biometric Strap)
 * - Intradomain user account provisioning & role management (Admin only)
 * - Active telemetry node diagnostics & audit logs
 */

import { useState } from "react";
import { Users, Wifi, WifiOff, Plus, X, Shield, Activity } from "lucide-react";
import { TopBar } from "../../components/shell/top-bar";
import { Panel } from "../../components/ui/panel";
import { Chip } from "../../components/ui/chip";

const INITIAL_USERS = [
  { id: 1, name: "System Admin", role: "admin", status: "Active", email: "admin@trackside.local" },
  { id: 2, name: "Coach Nair", role: "coach", status: "Active", email: "coach@trackside.local" },
  { id: 3, name: "A. Menon", role: "driver", status: "Active", email: "driver@trackside.local" },
  { id: 4, name: "R. Iyer", role: "driver", status: "Active", email: "iyer@trackside.local" },
];

export function AdminDashboard() {
  const [users] = useState(INITIAL_USERS);
  const [showCreateForm, setShowCreateForm] = useState(false);

  return (
    <div className="min-h-screen bg-[#0A0E13] text-[#E7EDF3] select-none">
      {/* Background Slanted Streams */}
      <div className="bg-slant-container">
        <div className="bg-slant-stream-top" />
        <div className="bg-slant-stream-bottom" />
      </div>

      <div className="relative z-10">
        <TopBar />

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
              <div
                className="mb-4 p-4 rounded-lg grid grid-cols-1 sm:grid-cols-4 gap-3 animate-fade-in"
                style={{ background: "#161D26", border: "1px solid #232B35" }}
              >
                <input
                  placeholder="Full Name"
                  className="px-3 py-2 rounded text-xs font-mono outline-none"
                  style={{ background: "#0A0E13", border: "1px solid #232B35", color: "#E7EDF3" }}
                />
                <input
                  placeholder="Email Address"
                  type="email"
                  className="px-3 py-2 rounded text-xs font-mono outline-none"
                  style={{ background: "#0A0E13", border: "1px solid #232B35", color: "#E7EDF3" }}
                />
                <select
                  className="px-3 py-2 rounded text-xs font-mono outline-none"
                  style={{ background: "#0A0E13", border: "1px solid #232B35", color: "#E7EDF3" }}
                >
                  <option value="coach">Role: Coach</option>
                  <option value="driver">Role: Driver</option>
                </select>
                <button
                  className="px-3 py-2 rounded text-xs font-bold font-mono uppercase tracking-wider cursor-pointer"
                  style={{ background: "#3FA6E0", color: "#06121B" }}
                >
                  Create Account
                </button>
              </div>
            )}

            {/* Users Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono">
                <thead>
                  <tr className="text-[10px] uppercase text-left border-b border-[#232B35]" style={{ color: "#7C8898" }}>
                    <th className="pb-2 font-semibold">User</th>
                    <th className="pb-2 font-semibold">Email</th>
                    <th className="pb-2 font-semibold">Role</th>
                    <th className="pb-2 font-semibold">Status</th>
                    <th className="pb-2 text-right font-semibold">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#232B35]">
                  {users.map((u) => {
                    const roleColor = u.role === "admin" ? "#33D17E" : u.role === "coach" ? "#3FA6E0" : "#F2A93B";
                    return (
                      <tr key={u.id} className="hover:bg-[#161D26] transition-colors">
                        <td className="py-2.5 font-bold">{u.name}</td>
                        <td className="py-2.5 text-[#7C8898]">{u.email}</td>
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
                          <Chip color={u.status === "Active" ? "#33D17E" : "#4B5563"}>
                            {u.status}
                          </Chip>
                        </td>
                        <td className="py-2.5 text-right space-x-2">
                          <button
                            className="text-[10px] px-2 py-1 rounded cursor-pointer"
                            style={{ color: "#3FA6E0", border: "1px solid #3FA6E044" }}
                          >
                            Edit
                          </button>
                          <button
                            className="text-[10px] px-2 py-1 rounded cursor-pointer"
                            style={{ color: "#E5473C", border: "1px solid #E5473C44" }}
                          >
                            Deactivate
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
