/**
 * Trackside Driver Dashboard — Session Mode Selector Panel.
 * Lets the driver switch between Safety Mode and Performance Mode focus.
 */

import { Flag } from "lucide-react";
import { Panel } from "../../../components/ui/panel";

interface ModeSelectorPanelProps {
  mode: "safety" | "performance";
  setMode: (mode: "safety" | "performance") => void;
}

export function ModeSelectorPanel({ mode, setMode }: ModeSelectorPanelProps) {
  return (
    <Panel testId="driver-panel-mode" title="Session Mode Setup" icon={Flag}>
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto font-mono">
          <button
            data-testid="driver-mode-safety-btn"
            onClick={() => setMode("safety")}
            className="text-xs font-mono font-bold px-4 py-2.5 min-h-[44px] flex-1 sm:flex-initial rounded transition-all duration-150 cursor-pointer flex items-center justify-center"
            style={{
              background: mode === "safety" ? "#3FA6E0" : "transparent",
              color: mode === "safety" ? "#06121B" : "#7C8898",
              border: `1px solid ${mode === "safety" ? "#3FA6E0" : "#232B35"}`,
              boxShadow: mode === "safety" ? "0 0 12px rgba(63,166,224,0.3)" : "none",
            }}
          >
            SAFETY MODE
          </button>
          <button
            data-testid="driver-mode-performance-btn"
            onClick={() => setMode("performance")}
            className="text-xs font-mono font-bold px-4 py-2.5 min-h-[44px] flex-1 sm:flex-initial rounded transition-all duration-150 cursor-pointer flex items-center justify-center"
            style={{
              background: mode === "performance" ? "#3FA6E0" : "transparent",
              color: mode === "performance" ? "#06121B" : "#7C8898",
              border: `1px solid ${mode === "performance" ? "#3FA6E0" : "#232B35"}`,
              boxShadow: mode === "performance" ? "0 0 12px rgba(63,166,224,0.3)" : "none",
            }}
          >
            PERFORMANCE MODE
          </button>
        </div>

        <span className="text-xs font-mono text-[#7C8898]">
          Active Focus:{" "}
          <span data-testid="driver-active-mode-text" className="text-[#3FA6E0] font-bold uppercase">
            {mode} Focus
          </span>
        </span>
      </div>
    </Panel>
  );
}
