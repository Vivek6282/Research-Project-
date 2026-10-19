/**
 * Trackside Coach Dashboard — Telemetry & WebSocket Streaming Hook.
 * Manages live WebSocket connection to Django Channels and local mock telemetry engine.
 */

import { useState, useEffect } from "react";
import { startMockTelemetryEngine } from "../../../lib/mockTelemetry";
import { DriverProfile } from "../types";

export const USE_MOCK_TELEMETRY = import.meta.env.VITE_USE_MOCK_TELEMETRY !== "false";

export function useCoachTelemetry(selectedDriver: DriverProfile, activeSessionId: string | null) {
  const [currentSpeed, setCurrentSpeed] = useState(selectedDriver.baseSpeed);
  const [currentHr, setCurrentHr] = useState(selectedDriver.baseHr);
  const [currentSpo2, setCurrentSpo2] = useState(selectedDriver.baseSpo2);
  const [currentBreathing, setCurrentBreathing] = useState(selectedDriver.baseBreathing);
  const [currentGForce, setCurrentGForce] = useState(1.42);
  const [currentGpsLat, setCurrentGpsLat] = useState<number | null>(null);
  const [currentGpsLng, setCurrentGpsLng] = useState<number | null>(null);
  const [wsStatus, setWsStatus] = useState<"connected" | "reconnecting" | "disconnected">("disconnected");

  const [actualSpeedPath, setActualSpeedPath] = useState<number[]>([
    110, 105, 90, 70, 60, 65, 80, 110, 125, 130, 115, 85, 65, 75, 95, 105,
  ]);
  const [targetSpeedPath] = useState<number[]>([
    100, 95, 85, 65, 55, 60, 75, 105, 120, 125, 110, 80, 60, 70, 90, 100,
  ]);

  const [hrHistory, setHrHistory] = useState<number[]>([30, 25, 20, 15, 22, 18, 25, 20, 15, 24]);
  const [spo2History, setSpo2History] = useState<number[]>([15, 18, 22, 20, 16, 18, 22, 19, 17, 15]);
  const [breathingHistory, setBreathingHistory] = useState<number[]>([25, 28, 20, 22, 26, 24, 28, 20, 22, 25]);

  // Sync state when driver changes
  useEffect(() => {
    setCurrentSpeed(selectedDriver.baseSpeed);
    setCurrentHr(selectedDriver.baseHr);
    setCurrentSpo2(selectedDriver.baseSpo2);
    setCurrentBreathing(selectedDriver.baseBreathing);
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
          if (USE_MOCK_TELEMETRY) return;
          try {
            const message = JSON.parse(event.data);
            if (message.type === "telemetry_reading" && message.data) {
              const { speed_kmh, lateral_g, gps_lat, gps_lng } = message.data;
              if (typeof speed_kmh === "number") {
                setCurrentSpeed(Math.round(speed_kmh));
                setActualSpeedPath((prev) => [...prev.slice(1), Math.round(speed_kmh)]);
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
              if (heart_rate) {
                setCurrentHr(heart_rate);
                setHrHistory((prev) => [...prev.slice(1), heart_rate]);
              }
              if (spo2) {
                setCurrentSpo2(spo2);
                setSpo2History((prev) => [...prev.slice(1), spo2]);
              }
              if (breathing_rate) {
                setCurrentBreathing(breathing_rate);
                setBreathingHistory((prev) => [...prev.slice(1), breathing_rate]);
              }
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

  // Mock telemetry generator effect
  useEffect(() => {
    if (!USE_MOCK_TELEMETRY) return;

    const stopMock = startMockTelemetryEngine(selectedDriver, (packet) => {
      setCurrentSpeed(packet.speed);
      setCurrentGForce(packet.gForce);
      setCurrentHr(packet.hr);
      setCurrentSpo2(packet.spo2);
      setCurrentBreathing(packet.breathing);
      setActualSpeedPath((prev) => [...prev.slice(1), packet.oscilloscopeVal]);
    });

    return () => stopMock();
  }, [selectedDriver]);

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
    targetSpeedPath,
    hrHistory,
    spo2History,
    breathingHistory,
    isMockTelemetry: USE_MOCK_TELEMETRY,
  };
}
