/**
 * Trackside — Top Bar Component
 *
 * Pit-Wall persistent header across all dashboards:
 * - 5-segment LED signal strip
 * - T R A C K S I D E branding
 * - System Online status badge
 * - Active Role indicator tag (COACH, ADMIN, DRIVER)
 * - User info & Sign out action
 */

import { LogOut } from "lucide-react";
import { useAuth } from "../../lib/auth";

export function TopBar() {
  const { user, logout } = useAuth();

  if (!user) return null;

  return (
    <div
      className="border-b sticky top-0 z-50 backdrop-blur-md select-none"
      style={{
        borderColor: "#232B35",
        background: "rgba(10, 14, 19, 0.95)",
        boxShadow: "0 4px 20px rgba(0, 0, 0, 0.6)",
      }}
    >
      <div className="max-w-[1400px] mx-auto px-4 py-2.5 flex items-center justify-between">
        {/* Left: Brand, Role Badge & Circuit Meta */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-base">🏁</span>
            <span
              className="text-sm font-bold font-sans tracking-[0.25em] uppercase text-[#E7EDF3]"
            >
              TRACKSIDE
            </span>
            <span
              className="text-[10px] font-sans font-bold px-1.5 py-0.5 rounded-[2px] uppercase tracking-wider bg-[#3FA6E0] text-[#0A0E13]"
            >
              COACH
            </span>
          </div>
          <span className="text-[#232B35]">|</span>
          <div className="flex items-center gap-2 text-[11px] font-mono text-[#7C8898] tracking-wider uppercase">
            <span>APEX ACADEMY</span>
            <span>·</span>
            <span>CIRCUIT NODE 7</span>
            <span>·</span>
            <span className="text-[#E7EDF3]">12:04:38</span>
          </div>
        </div>

        {/* Right: User Profile & Actions */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-2 py-1 rounded bg-[#161D26] border border-[#232B35] text-xs font-mono text-[#E7EDF3]">
            <span className="w-5 h-5 rounded-[2px] bg-[#232B35] text-[#3FA6E0] font-bold flex items-center justify-center text-[10px]">
              CR
            </span>
            <span className="font-semibold">{user.name || "Coach Rivera"}</span>
            <span className="text-[#7C8898] text-[10px]">▾</span>
          </div>

          <button
            onClick={logout}
            className="flex items-center gap-1 text-[11px] font-mono px-2.5 py-1 rounded cursor-pointer transition-colors hover:text-[#E5473C] text-[#7C8898] border border-[#232B35] bg-[#161D26]"
          >
            <LogOut size={13} />
            <span className="hidden sm:inline">Sign out</span>
          </button>
        </div>
      </div>
    </div>
  );
}
