/**
 * Trackside Coach Dashboard — Telemetry & WebSocket Streaming Hook.
 * Manages live WebSocket connection to Django Channels telemetry streams.
 */

import { useState, useEffect } from "react";
import { DriverProfile } from "../types";

export function useCoachTelemetry(selectedDriver: DriverProfile, activeSessionId: string | null) {
  const [currentSpeed, setCurrentSpeed] = useState<number | null>(null);
  const [currentHr, setCurrentHr] = useState(selectedDriver?.baseHr ?? 0);
  const [currentSpo2, setCurrentSpo2] = useState(selectedDriver?.baseSpo2 ?? 0);
  const [currentBreathing, setCurrentBreathing] = useState(selectedDriver?.baseBreathing ?? 0);
  const [currentGForce, setCurrentGForce] = useState<number | null>(null);
  const [currentGpsLat, setCurrentGpsLat] = useState<number | null>(null);
  const [currentGpsLng, setCurrentGpsLng] = useState<number | null>(null);
  const [wsStatus, setWsStatus] = useState<"connected" | "reconnecting" | "disconnected">("disconnected");

  const [actualSpeedPath, setActualSpeedPath] = useState<number[]>([]);


  // Sync state when driver changes
  useEffect(() => {
    setCurrentSpeed(null);
    setCurrentGForce(null);
    setCurrentGpsLat(null);
    setCurrentGpsLng(null);
    setCurrentHr(selectedDriver?.baseHr ?? 0);
    setCurrentSpo2(selectedDriver?.baseSpo2 ?? 0);
    setCurrentBreathing(selectedDriver?.baseBreathing ?? 0);
    setActualSpeedPath([]);
  }, [selectedDriver]);

  // WebSocket telemetry connection
  useEffect(() => {
    if (!activeSessionId) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/sessions/${activeSessionId}/telemetry/`;

    let ws: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const connectWebSocket = () => {
      try {
        ws = new WebSocket(wsUrl);
        setWsStatus("reconnecting");

        ws.onopen = () => {
          setWsStatus("connected");
        };

        ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            if (message.type === "telemetry_reading" && message.data) {
              const { speed_kmh, lateral_g, gps_lat, gps_lng } = message.data;
              if (typeof speed_kmh === "number") {
                setCurrentSpeed(Math.round(speed_kmh));
                setActualSpeedPath((prev) => {
                  const next = [...prev, Math.round(speed_kmh)];
                  return next.length > 20 ? next.slice(next.length - 20) : next;
                });
              }
              if (typeof lateral_g === "number") {
                setCurrentGForce(Number(lateral_g.toFixed(2)));
              }
              if (typeof gps_lat === "number" && typeof gps_lng === "number") {
                setCurrentGpsLat(gps_lat);
                setCurrentGpsLng(gps_lng);
              }
            } else if (message.type === "biometric_reading" && message.data) {
              const { heart_rate, spo2, breathing_rate } = message.data;
              if (heart_rate) setCurrentHr(heart_rate);
              if (spo2) setCurrentSpo2(spo2);
              if (breathing_rate) setCurrentBreathing(breathing_rate);
            }
          } catch (e) {
            console.warn("Error parsing incoming WebSocket telemetry packet:", e);
          }
        };

        ws.onclose = () => {
          setWsStatus("disconnected");
          reconnectTimer = setTimeout(connectWebSocket, 3000);
        };

        ws.onerror = () => {
          setWsStatus("disconnected");
          ws?.close();
        };
      } catch (err) {
        setWsStatus("disconnected");
        reconnectTimer = setTimeout(connectWebSocket, 3000);
      }
    };

    connectWebSocket();

    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (ws) ws.close();
    };
  }, [activeSessionId]);

  return {
    currentSpeed,
    currentHr,
    currentSpo2,
    currentBreathing,
    currentGForce,
    currentGpsLat,
    currentGpsLng,
    wsStatus,
    actualSpeedPath,
  };
}
