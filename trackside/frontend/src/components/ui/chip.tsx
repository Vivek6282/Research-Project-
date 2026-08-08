/**
 * Trackside — Chip Component
 *
 * Small status label with colored border and text.
 * Used for alert severity badges, connection status, etc.
 */

import type { ReactNode } from "react";

interface ChipProps {
  children: ReactNode;
  color: string;
}

export function Chip({ children, color }: ChipProps) {
  return (
    <span
      className="px-2 py-0.5 rounded text-xs font-mono tracking-wide"
      style={{
        color,
        border: `1px solid ${color}55`,
        background: `${color}14`,
      }}
    >
      {children}
    </span>
  );
}
