/**
 * Trackside Coach Dashboard — Active Session Hook.
 * Finds the session the coach is watching: the newest session of the SELECTED driver
 * (an in-progress one first, but only while the driver is live: an old session that was never
 * closed must not hide a newer finished run), and gives its id and its own track. Reloads the session
 * list when the tab changes and when the driver's session_state or live flag changes
 * in the roster (for example a new demo run started).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../../../lib/api";
import { HistoricalSession, RosterStatusItem } from "../types";

/**
 * The newest session of one driver. When preferInProgress is true (the driver is live) a session that has
 * not ended wins; otherwise the newest session wins, so a stale unfinished one cannot hide a newer run.
 */
export function pickActiveSession(sessionList: any[], driverId: string, preferInProgress = true): any | null {
  const mine = sessionList.filter((s) => driverId && s.driver === driverId);
  const newestFirst = (a: any, b: any) => String(b.started_at || "").localeCompare(String(a.started_at || ""));
  const inProgress = preferInProgress ? mine.filter((s) => !s.ended_at).sort(newestFirst) : [];
  return inProgress[0] || [...mine].sort(newestFirst)[0] || null;
}

/** The track id of a session, whether the API sends an id or a nested object; null when it has none. */
export function trackIdOf(session: any): string | null {
  const track = session?.track;
  return (typeof track === "object" ? track?.id : track) || null;
}

/** One row of the Historical Sessions list. */
function toHistoricalRow(s: any): HistoricalSession & { trackName?: string } {
  return {
    id: s.id.length > 8 ? `SESS-${s.id.slice(0, 4).toUpperCase()}` : s.id,
    rawId: s.id,
    driver: s.driver_name || "—",
    driverCode: s.driver_code ?? null,
    kart: s.kart || "—",
    trackName: s.track_name || s.track?.name || "",
    date: s.started_at ? new Date(s.started_at).toISOString().split("T")[0] : "—",
    duration: s.duration || "—",
    mode: s.mode ? s.mode.charAt(0).toUpperCase() + s.mode.slice(1) : "—",
    laps: s.laps ?? "—",
    bestLap: s.best_lap || "—",
    maxG: s.max_g || "—",
    alerts: s.alert_count ?? 0,
    isDemo: Boolean(s.is_demo),
  };
}

export function useActiveSession(selectedDriverId: string, rosterItem: RosterStatusItem | undefined, activeTab: string) {
  const [sessionList, setSessionList] = useState<any[]>([]);
  const [historicalSessions, setHistoricalSessions] = useState<HistoricalSession[]>([]);
  const [sessionsError, setSessionsError] = useState<string | null>(null);

  // Load all sessions the coach may see
  const loadSessions = useCallback(async () => {
    try {
      setSessionsError(null);
      const res = await api.get<any>("/api/sessions/");
      const list = Array.isArray(res) ? res : res.results || [];
      setSessionList(list);
      setHistoricalSessions(list.map(toHistoricalRow));
    } catch (err) {
      console.warn("Failed loading sessions from API:", err);
      setSessionsError("Failed to load historical sessions. Please try again.");
      setSessionList([]);
      setHistoricalSessions([]);
    }
  }, []);

  // Reload on every tab change so a run started meanwhile shows up
  useEffect(() => {
    loadSessions();
  }, [activeTab, loadSessions]);

  // Reload when the selected driver's session state or live flag changes in the roster
  const rosterSignature = `${rosterItem?.session_state ?? ""}|${rosterItem?.live ?? ""}`;
  const previousSignature = useRef(rosterSignature);
  useEffect(() => {
    if (previousSignature.current === rosterSignature) return;
    previousSignature.current = rosterSignature;
    loadSessions();
  }, [rosterSignature, loadSessions]);

  const isLive = rosterItem?.live === true;
  const active = useMemo(() => pickActiveSession(sessionList, selectedDriverId, isLive), [sessionList, selectedDriverId, isLive]);

  return {
    historicalSessions,
    sessionsError,
    retryLoadSessions: loadSessions,
    activeSessionId: (active?.id as string | undefined) ?? null,
    activeTrackId: trackIdOf(active),
    activeTrackName: (active?.track_name as string | undefined) || null,
  };
}
