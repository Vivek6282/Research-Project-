/**
 * Trackside — Login Form Component (Pit-Wall Access Card).
 * Renders the role switcher, identifier/password fields, and sign-in button.
 */

import { useLoginForm } from "../../hooks/use-login-form";

export function LoginForm() {
  const {
    selectedRole,
    identifier,
    setIdentifier,
    password,
    setPassword,
    isSubmitting,
    error,
    handleRoleSelect,
    handleSubmit,
  } = useLoginForm();

  return (
    <div
      className="w-full rounded-[2px] overflow-hidden relative shadow-2xl"
      style={{
        background: "#12181F",
        border: "1px solid #232B35",
        boxShadow: "0 20px 45px rgba(0,0,0,0.85)",
      }}
    >
      {/* Red/White Diagonal Kerb Stripe Top Edge */}
      <div className="w-full h-[3px] hazard-stripe" />

      <div className="p-5">
        {/* Card Header: PIT-WALL ACCESS & SYSTEM ONLINE */}
        <div className="flex items-center justify-between mb-4">
          <span className="text-[10px] font-mono uppercase tracking-widest font-semibold text-[#7C8898]">
            PIT-WALL ACCESS
          </span>
          <div className="flex items-center gap-1 px-1.5 py-0.5 rounded-[2px] text-[9px] font-mono tracking-wider text-[#33D17E] bg-[#33D17E]/10 border border-[#33D17E]/30">
            <span className="w-1.5 h-1.5 rounded-full bg-[#33D17E] animate-pulse" />
            SYSTEM ONLINE
          </div>
        </div>

        {/* Error Banner */}
        {error && (
          <div
            data-testid="login-error"
            className="rounded-[2px] px-3 py-1.5 mb-3 text-[11px] font-mono bg-[#E5473C]/15 border border-[#E5473C]/40 text-[#E5473C]"
          >
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3.5" data-testid="login-form">
          {/* Segmented Role Selector */}
          <div>
            <label className="block text-[9px] font-mono uppercase tracking-wider mb-1 text-[#7C8898]">
              ROLE
            </label>
            <div className="grid grid-cols-3 gap-0 rounded-[2px] overflow-hidden p-0.5 bg-[#161D26] border border-[#232B35]">
              {(["coach", "admin", "driver"] as const).map((role) => {
                const isActive = selectedRole === role;
                return (
                  <button
                    key={role}
                    type="button"
                    data-testid={`login-role-tab-${role}`}
                    onClick={() => handleRoleSelect(role)}
                    className="py-2.5 min-h-[40px] text-[10px] font-sans font-bold uppercase tracking-wider transition-all duration-150 rounded-[2px] cursor-pointer"
                    style={{
                      background: isActive ? "#3FA6E0" : "transparent",
                      color: isActive ? "#ffffff" : "#7C8898",
                    }}
                  >
                    {role}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Identifier Text Field */}
          <div>
            <label className="block text-[9px] font-mono uppercase tracking-wider mb-1 text-[#7C8898]">
              EMAIL OR DRIVER ID
            </label>
            <input
              type="text"
              data-testid="login-identifier-input"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder="Email or Driver ID (e.g. TRK-DRV-000042)"
              required
              className="w-full px-3 py-2.5 min-h-[44px] rounded-[2px] text-xs font-mono outline-none transition-colors bg-[#0A0E13] border border-[#232B35] text-[#E7EDF3] placeholder-[#4B5563] focus:border-[#3FA6E0]"
            />
          </div>

          {/* Monospace Access Code Field */}
          <div>
            <label className="block text-[9px] font-mono uppercase tracking-wider mb-1 text-[#7C8898]">
              ACCESS CODE
            </label>
            <input
              type="password"
              data-testid="login-password-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              className="w-full px-3 py-2.5 min-h-[44px] rounded-[2px] text-xs font-mono outline-none transition-colors bg-[#0A0E13] border border-[#232B35] text-[#E7EDF3] placeholder-[#4B5563] focus:border-[#3FA6E0]"
            />
          </div>

          {/* Primary Electric Blue Sign In Button */}
          <button
            type="submit"
            data-testid="login-submit-btn"
            disabled={isSubmitting}
            className="w-full py-3 min-h-[44px] rounded-[2px] text-xs font-bold font-sans uppercase tracking-wider transition-colors cursor-pointer disabled:opacity-50 mt-1 shadow-md bg-[#3FA6E0] text-white hover:bg-[#3595cb] flex items-center justify-center"
          >
            {isSubmitting ? "AUTHENTICATING…" : "SIGN IN"}
          </button>
        </form>

        {/* Muted Helper Line */}
        <p className="text-center text-[10px] font-sans text-[#7C8898] mt-3">
          Contact your academy administrator for credentials.
        </p>
      </div>
    </div>
  );
}
