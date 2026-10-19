/**
 * Trackside Admin Dashboard — User Create Form & Credentials Component.
 * Allows administrators to provision new driver/coach accounts and display
 * generated credentials with one-click clipboard copy.
 */

import { Check, Copy } from "lucide-react";
import { SuccessData } from "../types";

interface UserCreateFormProps {
  showCreateForm: boolean;
  name: string;
  setName: (v: string) => void;
  email: string;
  setEmail: (v: string) => void;
  role: "coach" | "driver";
  setRole: (v: "coach" | "driver") => void;
  password: string;
  setPassword: (v: string) => void;
  errorMsg: string;
  handleCreateAccount: () => void;
  successData: SuccessData | null;
  copied: boolean;
  copyCredentials: () => void;
}

export function UserCreateForm({
  showCreateForm,
  name,
  setName,
  email,
  setEmail,
  role,
  setRole,
  password,
  setPassword,
  errorMsg,
  handleCreateAccount,
  successData,
  copied,
  copyCredentials,
}: UserCreateFormProps) {
  return (
    <>
      {/* Inline Account Creation Form (Admin Only) */}
      {showCreateForm && (
        <div
          data-testid="admin-create-form"
          className="mb-4 p-4 rounded-lg space-y-3 animate-fade-in bg-[#161D26] border border-[#232B35]"
        >
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
            <input
              data-testid="admin-create-name-input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Full Name"
              className="px-3 py-2 rounded text-xs font-mono outline-none bg-[#0A0E13] border border-[#232B35] text-[#E7EDF3] focus:border-[#3FA6E0]"
            />
            <select
              data-testid="admin-create-role-select"
              value={role}
              onChange={(e) => setRole(e.target.value as "coach" | "driver")}
              className="px-3 py-2 rounded text-xs font-mono outline-none bg-[#0A0E13] border border-[#232B35] text-[#E7EDF3] focus:border-[#3FA6E0]"
            >
              <option value="driver">Role: Driver</option>
              <option value="coach">Role: Coach</option>
            </select>
            <input
              data-testid="admin-create-email-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder={role === "driver" ? "Email (optional for Drivers)" : "Email address (required)"}
              type="email"
              className="px-3 py-2 rounded text-xs font-mono outline-none bg-[#0A0E13] border border-[#232B35] text-[#E7EDF3] focus:border-[#3FA6E0]"
            />
            <input
              data-testid="admin-create-password-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Access Password (min 8 chars)"
              type="password"
              className="px-3 py-2 rounded text-xs font-mono outline-none bg-[#0A0E13] border border-[#232B35] text-[#E7EDF3] focus:border-[#3FA6E0]"
            />
          </div>

          <div className="flex items-center justify-between pt-1">
            <span className="text-[10px] font-mono text-[#7C8898]">
              {role === "driver"
                ? "💡 Driver ID username will be auto-generated server-side (e.g. TRK-DRV-000042)"
                : "💡 Coach email is required for alert & session notifications."}
            </span>
            <button
              data-testid="admin-create-submit-btn"
              onClick={handleCreateAccount}
              className="px-4 py-2 rounded text-xs font-bold font-mono uppercase tracking-wider cursor-pointer bg-[#3FA6E0] text-[#06121B] hover:bg-[#3FA6E0]/90 transition-colors"
            >
              Create Account
            </button>
          </div>

          {errorMsg && (
            <div
              data-testid="admin-create-error"
              className="p-2 rounded text-xs font-mono bg-[#E5473C]/15 border border-[#E5473C]/40 text-[#E5473C]"
            >
              {errorMsg}
            </div>
          )}
        </div>
      )}

      {/* Generated Credentials Confirmation Panel */}
      {successData && (
        <div
          data-testid="admin-create-success"
          className="mb-4 p-4 rounded-lg font-mono bg-[#33D17E]/10 border border-[#33D17E]/40 text-[#E7EDF3]"
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Check size={16} className="text-[#33D17E]" />
              <span className="text-xs font-bold text-[#33D17E] uppercase">
                Account Provisioned Successfully — {successData.name} ({successData.role})
              </span>
            </div>
            <button
              data-testid="admin-create-copy-btn"
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
              <span
                data-testid="admin-create-success-username"
                className="text-[#3FA6E0] font-extrabold text-sm"
              >
                {successData.username}
              </span>
            </div>
            <div>
              <span className="text-[#7C8898] block text-[10px]">ACCESS PASSWORD:</span>
              <span className="text-[#E7EDF3] font-bold text-sm">
                {successData.password}
              </span>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
