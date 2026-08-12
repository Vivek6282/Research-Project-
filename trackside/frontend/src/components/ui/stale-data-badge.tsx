/**
 * Trackside — Stale Data / Offline Indicator Badge
 *
 * Displays a visible "Last synced: X minutes ago" or "OFFLINE CACHED DATA" status tag
 * so driver-module and pit-wall metrics are never presented as live when using cached data.
 */

import { useState, useEffect } from "react";
import { WifiOff, Clock } from "lucide-react";

interface StaleDataBadgeProps {
  lastSyncedTimestamp?: number; // epoch ms
  isOffline?: boolean;
}

export function StaleDataBadge({ lastSyncedTimestamp, isOffline: forceOffline }: StaleDataBadgeProps) {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [minutesAgo, setMinutesAgo] = useState(0);

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  useEffect(() => {
    if (!lastSyncedTimestamp) return;

    const updateDiff = () => {
      const diffMs = Date.now() - lastSyncedTimestamp;
      const mins = Math.max(0, Math.floor(diffMs / 60000));
      setMinutesAgo(mins);
    };

    updateDiff();
    const interval = setInterval(updateDiff, 30000);
    return () => clearInterval(interval);
  }, [lastSyncedTimestamp]);

  const offline = forceOffline || !isOnline;

  if (!offline && minutesAgo < 1) {
    return null; // Data is fresh and online
  }

  return (
    <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-[2px] font-mono text-[10px] font-bold uppercase select-none transition-all bg-[#161D26] border border-[#232B35] text-[#F2A93B]">
      {offline ? <WifiOff size={11} className="text-[#E5473C]" /> : <Clock size={11} className="text-[#F2A93B]" />}
      <span>
        {offline
          ? `OFFLINE · CACHED (${minutesAgo}M AGO)`
          : `LAST SYNCED: ${minutesAgo === 0 ? "JUST NOW" : `${minutesAgo}M AGO`}`}
      </span>
    </div>
  );
}
