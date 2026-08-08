/**
 * Trackside — Dev Banner Component
 *
 * Yellow motorsport hazard caution banner wrapping Phase 1.5 & Phase 2 features.
 * Muted content inside is clearly non-interactive to signal ongoing development.
 */

import type { ReactNode } from "react";
import { Construction } from "lucide-react";

interface DevBannerProps {
  phase: string;
  children: ReactNode;
}

export function DevBanner({ phase, children }: DevBannerProps) {
  return (
    <div
      className="rounded-lg overflow-hidden relative shadow-lg"
      style={{ border: "1px solid #E8C54744" }}
    >
      {/* Top Yellow Caution Stripe */}
      <div className="w-full h-1 hazard-stripe-yellow" />

      {/* Header bar */}
      <div
        className="flex items-center justify-between px-3.5 py-2"
        style={{ background: "rgba(232, 197, 71, 0.12)" }}
      >
        <div className="flex items-center gap-2">
          <Construction size={14} style={{ color: "#E8C547" }} />
          <span
            className="text-[11px] font-mono font-bold uppercase tracking-widest"
            style={{ color: "#E8C547" }}
          >
            {phase} — DEVELOPMENT ONGOING
          </span>
        </div>
        <span
          className="text-[9px] font-mono px-1.5 py-0.5 rounded uppercase"
          style={{
            background: "#E8C54720",
            color: "#E8C547",
            border: "1px solid #E8C54744",
          }}
        >
          PLANNED FEATURE
        </span>
      </div>

      {/* Muted content container */}
      <div
        className="p-4 pointer-events-none select-none"
        style={{ background: "#12181F", opacity: 0.7 }}
      >
        {children}
      </div>
    </div>
  );
}
