/**
 * Trackside Driver Dashboard — Data Fetching and Live Telemetry Hook.
 * Fetches recent session alert history, session goals, and manages real-time
 * or simulated lateral g-force sensor streams.
 */

import { useState, useEffect } from "react";
import { api } from "../../../lib/api";

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
  best_lap_time?: string;
  is_demo?: boolean;
}

export function useDriverDashboard() {
  const [mode, setMode] = useState<"safety" | "performance">("safety");
  const [currentG, setCurrentG] = useState<number | null>(null);
  const [lastSyncTime, setLastSyncTime] = useState<number>(Date.now());
  const [zones, setZones] = useState<ZoneSummary[]>([]);
  const [hasSessions, setHasSessions] = useState<boolean>(true);
  const [latestSession, setLatestSession] = useState<LatestSessionData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const activeZone = zones.length > 0 ? zones[0].name : null;
  const activeThreshold = zones.length > 0 && typeof zones[0].threshold === "number" ? zones[0].threshold : null;

  // 1. Fetch real driver-scoped zone alert summary & session goals
  useEffect(() => {
    async function loadDriverSummary() {
      try {
        setLoading(true);
        const responseData: any = await api.get("/api/sessions/alerts/summary/");
        if (responseData) {
          setHasSessions(responseData.has_sessions !== false);
          setZones(Array.isArray(responseData.zones) ? responseData.zones : []);
          setLatestSession(responseData.latest_session || null);
          if (responseData.latest_session?.mode) {
            setMode(responseData.latest_session.mode.toLowerCase() as "safety" | "performance");
          }
        }
      } catch (err: any) {
        console.warn("[useDriverDashboard] loadDriverSummary failure:", err);
        setHasSessions(false);
      } finally {
        setLoading(false);
      }
    }
    loadDriverSummary();
  }, []);

  // 2. Real-time driver G-Force telemetry streaming via WebSocket
  useEffect(() => {
    if (!latestSession?.id) return;

    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsHost = window.location.host;
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const connectSocket = () => {
      try {
        socket = new WebSocket(`${wsProtocol}//${wsHost}/ws/sessions/${latestSession.id}/telemetry/`);

        socket.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            if (message.type === "telemetry_reading" && message.data) {
              const { lateral_g } = message.data;
              if (typeof lateral_g === "number") {
                setCurrentG(Number(lateral_g.toFixed(2)));
                setLastSyncTime(Date.now());
              }
            }
          } catch (e) {
            console.warn("[useDriverDashboard] WebSocket telemetry error:", e);
          }
        };

        socket.onclose = () => {
          reconnectTimer = setTimeout(connectSocket, 3000);
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
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (socket) socket.close();
    };
  }, [latestSession?.id]);

  return {
    mode,
    setMode,
    currentG,
    lastSyncTime,
    zones,
    hasSessions,
    latestSession,
    loading,
    activeThreshold,
    activeZone,
  };
}
