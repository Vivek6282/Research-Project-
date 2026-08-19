/**
 * Trackside — Top Bar Component
 *
 * Pit-Wall persistent header across all dashboards:
 * - T R A C K S I D E branding
 * - Dynamic Active Role indicator tag (COACH, ADMIN, DRIVER)
 * - Settings Gear action button (opens Settings Modal)
 * - User profile info & Sign out action
 */

import { LogOut, Settings } from "lucide-react";
import { useAuth } from "../../lib/auth";
import { usePreferences } from "../../context/PreferencesContext";
import { SettingsModal } from "../ui/settings-modal";

export function TopBar() {
  const { user, logout } = useAuth();
  const { openSettings } = usePreferences();

  if (!user) return null;

  const roleLabel = (user.role || "coach").toUpperCase();
  const userInitials = (user.name || user.email || "TS")
    .split(" ")
    .map((n) => n[0])
    .join("")
    .substring(0, 2)
    .toUpperCase();

  return (
    <>
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
          <div className="flex items-center gap-2 sm:gap-3">
            <div className="flex items-center gap-1.5 sm:gap-2">
              <span className="text-sm sm:text-base">🏁</span>
              <span className="text-xs sm:text-sm font-bold font-sans tracking-[0.2em] sm:tracking-[0.25em] uppercase text-[#E7EDF3]">
                TRACKSIDE
              </span>
              <span className="text-[9px] sm:text-[10px] font-sans font-bold px-1.5 py-0.5 rounded-[2px] uppercase tracking-wider bg-[#3FA6E0] text-[#0A0E13]">
                {roleLabel}
              </span>
            </div>
            <span className="text-[#232B35] hidden sm:inline">|</span>
            <div className="flex items-center gap-2 text-[11px] font-mono text-[#7C8898] tracking-wider uppercase hidden md:flex">
              <span>APEX ACADEMY</span>
              <span>·</span>
              <span>NODE 7</span>
            </div>
          </div>

          {/* Right: User Profile, Settings Gear & Sign Out */}
          <div className="flex items-center gap-1.5 sm:gap-3">
            <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-[#161D26] border border-[#232B35] text-xs font-mono text-[#E7EDF3] max-w-[120px] xs:max-w-[160px] sm:max-w-[220px]">
              <span className="w-5 h-5 rounded-[2px] bg-[#232B35] text-[#3FA6E0] font-bold flex-shrink-0 flex items-center justify-center text-[10px]">
                {userInitials}
              </span>
              <span className="font-semibold truncate text-[11px] sm:text-xs">{user.name || user.email}</span>
            </div>

            {/* Settings Gear Button */}
            <button
              onClick={openSettings}
              title="Display Settings"
              className="flex items-center justify-center w-8 h-8 rounded-[2px] bg-[#161D26] border border-[#232B35] text-[#7C8898] hover:text-[#3FA6E0] hover:border-[#3FA6E0] transition-all cursor-pointer min-h-[36px] min-w-[36px]"
            >
              <Settings size={15} />
            </button>

            {/* Sign Out Button */}
            <button
              onClick={logout}
              title="Sign Out"
              className="flex items-center gap-1 text-[11px] font-mono px-2.5 py-1.5 min-h-[36px] rounded cursor-pointer transition-colors hover:text-[#E5473C] text-[#7C8898] border border-[#232B35] bg-[#161D26]"
            >
              <LogOut size={14} />
              <span className="hidden sm:inline">Sign out</span>
            </button>
          </div>

        </div>
      </div>

      {/* Settings Modal Component */}
      <SettingsModal />
    </>
  );
}
