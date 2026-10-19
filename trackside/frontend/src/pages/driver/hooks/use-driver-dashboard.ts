/**
 * Trackside Driver Dashboard — Data Fetching and Live Telemetry Hook.
 * Fetches recent session alert history, session goals, and manages real-time
 * or simulated lateral g-force sensor streams.
 */

import { useState, useEffect } from "react";
import { api } from "../../../lib/api";

const USE_MOCK_TELEMETRY = import.meta.env.VITE_USE_MOCK_TELEMETRY !== "false";

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
}

export function useDriverDashboard() {
  const [mode, setMode] = useState<"safety" | "performance">("safety");
  const [currentG, setCurrentG] = useState(0.85);
  const [lastSyncTime, setLastSyncTime] = useState<number>(Date.now());
  const [zones, setZones] = useState<ZoneSummary[]>([]);
  const [hasSessions, setHasSessions] = useState<boolean>(true);
  const [latestSession, setLatestSession] = useState<LatestSessionData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const activeThreshold = 1.15; // Hairpin Zone Threshold

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

  // 2. Real-time driver G-Force telemetry streaming
  useEffect(() => {
    if (USE_MOCK_TELEMETRY) {
      const intervalId = setInterval(() => {
        const timeOffset = Date.now() / 400;
        const simulatedForce = Number((0.75 + Math.abs(Math.sin(timeOffset)) * 0.48).toFixed(2));
        setCurrentG(simulatedForce);
        setLastSyncTime(Date.now());
      }, 200);
      return () => clearInterval(intervalId);
    } else {
      const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const wsHost = window.location.hostname === "localhost" ? "localhost:8000" : window.location.host;
      const telemetrySocket = new WebSocket(`${wsProtocol}//${wsHost}/ws/telemetry/`);

      telemetrySocket.onmessage = (event) => {
        try {
          const packetData = JSON.parse(event.data);
          if (packetData && typeof packetData.gForce === "number") {
            setCurrentG(Number(packetData.gForce.toFixed(2)));
            setLastSyncTime(Date.now());
          }
        } catch (e) {
          console.warn("[useDriverDashboard] WebSocket telemetry error:", e);
        }
      };

      telemetrySocket.onerror = (err) => {
        console.warn("[useDriverDashboard] Telemetry WebSocket connection error:", err);
      };

      return () => {
        telemetrySocket.close();
      };
    }
  }, []);

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
    isMockTelemetry: USE_MOCK_TELEMETRY,
  };
}
