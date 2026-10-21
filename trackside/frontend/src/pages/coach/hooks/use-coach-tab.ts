/**
 * Trackside Coach — which tab of the Coach screen is open (Live, Historical, or Maps & Demo).
 * The link "/coach?tab=maps" (used by the top bar's Maps button) opens the Maps & Demo tab.
 */

import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

export type CoachTab = "live" | "history" | "maps";

/** Holds the open tab and follows the ?tab=maps link, even when the Coach screen is already open. */
export function useCoachTab() {
  const [searchParams] = useSearchParams();
  const wanted = searchParams.get("tab");
  const [activeTab, setActiveTab] = useState<CoachTab>(wanted === "maps" ? "maps" : "live");

  useEffect(() => {
    if (wanted === "maps") setActiveTab("maps");
  }, [wanted]);

  return { activeTab, setActiveTab };
}
