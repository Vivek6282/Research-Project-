/**
 * Trackside Driver Dashboard — Data Fetching and Live Telemetry Hook.
 * Keeps the driver's screen in step with the Coach screen: the summary (latest session, laps, alerts,
 * zone tiles) is re-read every few seconds, and the live readings of the latest session arrive over
 * the WebSocket, so a run the coach starts later shows up here without reloading the page.
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "../../../lib/api";
import { TrajectoryStage } from "../../../components/ui/signal-strip";

export interface ZoneSummary {
  name: string;
  count: number;
  red_count?: number;
  status: string;
  color: string;
  threshold: number;
}

export interface LatestSessionData {
  id: string;
  mode: string;
  goal_text: string;
  goal_passed: boolean | null;
  started_at: string;
  track_name: string;
  best_lap_time?: string | null;
  is_demo?: boolean;
  ended_at?: string | null;
  live?: boolean;
  laps?: number | string | null;
  alert_count?: number | null;
  duration?: string | null;
  max_g?: number | string | null;
}

/** How often the summary is read again (a new run, laps and alerts show up within this time). */
export const SUMMARY_REFRESH_MS = 3000;

export function useDriverDashboard() {
  const [mode, setMode] = useState<"safety" | "performance">("safety");
  const [currentG, setCurrentG] = useState<number | null>(null);
  const [liveZone, setLiveZone] = useState<string | null>(null);
  const [liveThreshold, setLiveThreshold] = useState<number | null>(null);
  const [liveStage, setLiveStage] = useState<TrajectoryStage | null>(null);
  const [lastSyncTime, setLastSyncTime] = useState<number | undefined>(undefined);
  const [zones, setZones] = useState<ZoneSummary[]>([]);
  const [hasSessions, setHasSessions] = useState<boolean>(true);
  const [latestSession, setLatestSession] = useState<LatestSessionData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const modeSetForSession = useRef<string | null>(null);

  /** Read the summary once. A failed refresh keeps what is on screen; only the first load can say "no sessions". */
  const loadSummary = useCallback(async (isFirstLoad: boolean) => {
    try {
      const responseData: any = await api.get("/api/sessions/alerts/summary/");
      if (!responseData) return;
      const session: LatestSessionData | null = responseData.latest_session || null;
      setHasSessions(responseData.has_sessions !== false);
      setZones(Array.isArray(responseData.zones) ? responseData.zones : []);
      setLatestSession(session);
      // The mode follows a new session; it is not reset on every refresh, so the driver's own pick stays.
      if (session?.mode && modeSetForSession.current !== session.id) {
        modeSetForSession.current = session.id;
        setMode(session.mode.toLowerCase() as "safety" | "performance");
      }
      // The run is over (or idle): nothing live to show any more.
      if (!session || session.live === false) {
        setCurrentG(null);
        setLiveZone(null);
        setLiveThreshold(null);
        setLiveStage(null);
      }
    } catch (err: any) {
      console.warn("[useDriverDashboard] loadDriverSummary failure:", err);
      if (isFirstLoad) setHasSessions(false);
    } finally {
      if (isFirstLoad) setLoading(false);
    }
  }, []);

  // 1. Read the summary now and then every few seconds while the page is open
  useEffect(() => {
    loadSummary(true);
    const timer = setInterval(() => {
      if (!document.hidden) loadSummary(false);
    }, SUMMARY_REFRESH_MS);
    return () => clearInterval(timer);
  }, [loadSummary]);

  // 2. Live readings of the latest session over the WebSocket (reconnects when the session changes)
  useEffect(() => {
    if (!latestSession?.id) return;

    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsHost = window.location.host;
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let closedByUs = false;

    const connectSocket = () => {
      try {
        socket = new WebSocket(`${wsProtocol}//${wsHost}/ws/sessions/${latestSession.id}/telemetry/`);

        socket.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            if (message.type === "telemetry_reading" && message.data) {
              const { lateral_g, zone_label, threshold, stage } = message.data;
              if (typeof lateral_g === "number") {
                setCurrentG(Number(lateral_g.toFixed(2)));
                setLiveZone(typeof zone_label === "string" ? zone_label : null);
                setLiveThreshold(typeof threshold === "number" ? threshold : null);
                // The server works the stage out with the corner's own limit, the same as the glove and the coach
                setLiveStage(stage === "monitoring" || stage === "intervene" ? stage : "nominal");
                setLastSyncTime(Date.now());
              }
            } else if (message.type === "alert_triggered") {
              loadSummary(false); // a new alert: refresh the counts and the zone tiles now
            }
          } catch (e) {
            console.warn("[useDriverDashboard] WebSocket telemetry error:", e);
          }
        };

        socket.onclose = () => {
          if (!closedByUs) reconnectTimer = setTimeout(connectSocket, 3000);
        };

        socket.onerror = (err) => {
          console.warn("[useDriverDashboard] Telemetry WebSocket connection error:", err);
          socket?.close();
        };
      } catch (err) {
        reconnectTimer = setTimeout(connectSocket, 3000);
      }
    };

    connectSocket();

    return () => {
      closedByUs = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (socket) socket.close();
    };
  }, [latestSession?.id, loadSummary]);

  return {
    mode,
    setMode,
    currentG,
    lastSyncTime,
    zones,
    hasSessions,
    latestSession,
    loading,
    liveStage,
    activeThreshold: liveThreshold,
    activeZone: liveZone,
  };
}
