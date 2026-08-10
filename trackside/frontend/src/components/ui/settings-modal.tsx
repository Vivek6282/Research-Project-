/**
 * Trackside — Settings Modal Component
 *
 * Pit-Wall styled settings modal for user preferences:
 * - Theme selection: Dark / Light
 * - Font Size presets: S (Small), M (Medium), L (Large), XL (Extra Large)
 * - Show tutorial again option
 * - Done button to close and persist preferences
 */

import { X, Sun, Moon, RotateCcw, Check } from "lucide-react";
import { usePreferences, type FontSizePreset } from "../../context/PreferencesContext";

export function SettingsModal() {
  const {
    theme,
    fontSize,
    isSettingsOpen,
    closeSettings,
    updatePreferences,
    replayTutorial,
  } = usePreferences();

  if (!isSettingsOpen) return null;

  const fontPresets: { label: string; value: FontSizePreset; hint: string }[] = [
    { label: "S", value: "small", hint: "14px" },
    { label: "M", value: "medium", hint: "16px" },
    { label: "L", value: "large", hint: "18px" },
    { label: "XL", value: "xlarge", hint: "20px" },
  ];

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/75 backdrop-blur-sm select-none p-4">
      <div className="w-full max-w-md bg-[#12181F] border border-[#232B35] rounded-[4px] shadow-2xl overflow-hidden font-mono text-[#E7EDF3] animate-in fade-in zoom-in-95 duration-150">
        {/* Header Bar */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#232B35] bg-[#161D26]">
          <div className="flex items-center gap-2">
            <span className="text-[#3FA6E0] font-bold text-sm">⚙️</span>
            <span className="text-xs font-bold uppercase tracking-wider text-[#E7EDF3]">
              PIT-WALL DISPLAY SETTINGS
            </span>
          </div>
          <button
            onClick={closeSettings}
            className="text-[#7C8898] hover:text-[#E7EDF3] p-1 rounded hover:bg-[#232B35] transition-colors cursor-pointer"
          >
            <X size={16} />
          </button>
        </div>

        {/* Modal Content Body */}
        <div className="p-5 space-y-6">
          {/* THEME SECTION */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-[#7C8898] uppercase tracking-wider">
                | THEME PRESET
              </span>
              <span className="text-[10px] text-[#3FA6E0]">SERVER PERSISTED</span>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => updatePreferences({ theme: "dark" })}
                className={`flex items-center justify-center gap-2 py-2.5 px-3 rounded-[2px] border text-xs font-bold cursor-pointer transition-all ${
                  theme === "dark"
                    ? "bg-[#3FA6E0]/15 border-[#3FA6E0] text-[#3FA6E0]"
                    : "bg-[#161D26] border-[#232B35] text-[#7C8898] hover:border-[#3A4553]"
                }`}
              >
                <Moon size={14} />
                <span>DARK MODE</span>
                {theme === "dark" && <Check size={12} className="ml-auto" />}
              </button>

              <button
                type="button"
                onClick={() => updatePreferences({ theme: "light" })}
                className={`flex items-center justify-center gap-2 py-2.5 px-3 rounded-[2px] border text-xs font-bold cursor-pointer transition-all ${
                  theme === "light"
                    ? "bg-[#3FA6E0]/15 border-[#3FA6E0] text-[#3FA6E0]"
                    : "bg-[#161D26] border-[#232B35] text-[#7C8898] hover:border-[#3A4553]"
                }`}
              >
                <Sun size={14} />
                <span>LIGHT MODE</span>
                {theme === "light" && <Check size={12} className="ml-auto" />}
              </button>
            </div>
          </div>

          {/* TEXT SIZE SECTION */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-[#7C8898] uppercase tracking-wider">
                | TEXT SIZE PRESET
              </span>
              <span className="text-[10px] text-[#7C8898]">GLOBAL ROOT SCALE</span>
            </div>
            <div className="grid grid-cols-4 gap-2">
              {fontPresets.map((preset) => {
                const isActive = fontSize === preset.value;
                return (
                  <button
                    key={preset.value}
                    type="button"
                    onClick={() => updatePreferences({ font_size: preset.value })}
                    className={`flex flex-col items-center justify-center py-2.5 px-2 rounded-[2px] border cursor-pointer transition-all ${
                      isActive
                        ? "bg-[#3FA6E0] text-[#0A0E13] border-[#3FA6E0] font-extrabold"
                        : "bg-[#161D26] text-[#7C8898] border-[#232B35] hover:border-[#3A4553] hover:text-[#E7EDF3]"
                    }`}
                  >
                    <span className="text-sm">{preset.label}</span>
                    <span className={`text-[9px] ${isActive ? "text-[#0A0E13]/80" : "text-[#7C8898]"}`}>
                      {preset.hint}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* REPLAY TUTORIAL SECTION */}
          <div className="pt-2 border-t border-[#232B35]">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-[#7C8898] uppercase tracking-wider">
                | ONBOARDING TUTORIAL
              </span>
            </div>
            <button
              type="button"
              onClick={replayTutorial}
              className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-[2px] bg-[#161D26] border border-[#232B35] text-[#3FA6E0] hover:border-[#3FA6E0] hover:bg-[#3FA6E0]/10 text-xs font-bold cursor-pointer transition-all"
            >
              <RotateCcw size={13} />
              <span>SHOW TUTORIAL AGAIN</span>
            </button>
          </div>
        </div>

        {/* Modal Footer Bar */}
        <div className="px-5 py-3 border-t border-[#232B35] bg-[#161D26] flex justify-end">
          <button
            type="button"
            onClick={closeSettings}
            className="px-5 py-1.5 rounded-[2px] bg-[#3FA6E0] text-[#0A0E13] font-bold text-xs hover:bg-[#3FA6E0]/90 transition-colors cursor-pointer"
          >
            DONE
          </button>
        </div>
      </div>
    </div>
  );
}
