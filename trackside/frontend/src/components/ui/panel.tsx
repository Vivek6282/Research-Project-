/**
 * Trackside — Panel Component
 *
 * Dark motorsport cockpit card container with header icon, title,
 * and metallic border.
 */

import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

interface PanelProps {
  title: string;
  icon?: LucideIcon;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Panel({ title, icon: Icon, right, children, className = "" }: PanelProps) {
  return (
    <div
      className={`rounded-lg p-4 transition-all duration-150 ${className}`}
      style={{
        background: "#12181F",
        border: "1px solid #232B35",
        boxShadow: "0 8px 24px rgba(0, 0, 0, 0.4)",
      }}
    >
      <div className="flex items-center justify-between mb-3.5 pb-2 border-b border-[#232B35]">
        <div className="flex items-center gap-2">
          {Icon && <Icon size={14} style={{ color: "#3FA6E0" }} />}
          <h3
            className="text-xs font-mono uppercase tracking-widest font-semibold"
            style={{ color: "#7C8898" }}
          >
            {title}
          </h3>
        </div>
        {right}
      </div>
      {children}
    </div>
  );
}
