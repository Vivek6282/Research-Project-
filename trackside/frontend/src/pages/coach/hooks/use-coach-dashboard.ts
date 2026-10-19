/**
 * Trackside Coach Dashboard — State Management Coordinator Hook.
 * Manages driver roster, threshold calibration, and composes telemetry and notes hooks.
 */

import { useState, useEffect } from "react";
import { api } from "../../../lib/api";
import { useCoachTelemetry } from "./use-coach-telemetry";
import { useCoachNotes } from "./use-coach-notes";
import {
  DriverProfile,
  HistoricalSession,
  RosterStatusItem,
} from "../types";
import {
  DEFAULT_SPRINT_FLOOR,
  DEFAULT_SPRINT_CEILING,
  INITIAL_DRIVERS,
  INITIAL_HISTORICAL_SESSIONS,
} from "../constants";

export { DEFAULT_SPRINT_FLOOR, DEFAULT_SPRINT_CEILING };

export function useCoachDashboard() {
  const [activeTab, setActiveTab] = useState<"live" | "history">("live");
  const [drivers, setDrivers] = useState<DriverProfile[]>(INITIAL_DRIVERS);
  const [selectedKart, setSelectedKart] = useState("12");
  const [thresholds, setThresholds] = useState<Record<string, number>>({
    "12": DEFAULT_SPRINT_CEILING,
    "7": 1.1,
    "3": 1.05,
    "18": DEFAULT_SPRINT_CEILING,
    "5": DEFAULT_SPRINT_FLOOR,
  });

  const [historicalSessions, setHistoricalSessions] = useState<HistoricalSession[]>(
    INITIAL_HISTORICAL_SESSIONS,
  );
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [activeTrackId, setActiveTrackId] = useState<string | null>(null);
  const [rosterMap, setRosterMap] = useState<Record<string, RosterStatusItem>>({});

  const selectedDriver =
    drivers.find((d) => d.kart === selectedKart) || drivers[0] || INITIAL_DRIVERS[0];

  // Compose telemetry hook
  const telemetry = useCoachTelemetry(selectedDriver, activeSessionId);

  // Compose notes & zones hook
  const notesManager = useCoachNotes(
    activeSessionId,
    activeTrackId,
    setActiveTrackId,
    selectedDriver,
  );

  const currentZoneObj =
    notesManager.zones.find((z) => z.id === notesManager.selectedZoneId) || notesManager.zones[0];
  const sliderMin = currentZoneObj?.min_threshold_g ?? DEFAULT_SPRINT_FLOOR;
  const sliderMax = currentZoneObj?.threshold_g ?? DEFAULT_SPRINT_CEILING;

  const selectedDriverMode = (selectedDriver?.session || "").toLowerCase().includes("safety")
    ? "Safety"
    : "Performance";
  const modeDefaultThreshold = selectedDriverMode === "Safety" ? sliderMin : sliderMax;
  const currentThreshold = thresholds[selectedKart] ?? modeDefaultThreshold;

  // Poll GET /api/sessions/roster-status/ every 2.5s for Timing Tower signal strips
  useEffect(() => {
    if (activeTab !== "live") return;

    async function fetchRosterStatus() {
      try {
        const res: any = await api.get("/api/sessions/roster-status/");
        if (res && Array.isArray(res.roster)) {
          const map: Record<string, RosterStatusItem> = {};
          res.roster.forEach((item: any) => {
            if (item.kart) {
              map[item.kart] = {
                current_g: item.current_g || 0.85,
                active_threshold: item.active_threshold || DEFAULT_SPRINT_CEILING,
                stage: item.stage || "nominal",
              };
            }
          });
          setRosterMap(map);
        }
      } catch (err) {
        console.warn("Roster status polling error:", err);
      }
    }

    fetchRosterStatus();
    const interval = setInterval(fetchRosterStatus, 2500);
    return () => clearInterval(interval);
  }, [activeTab]);

  // Fetch Drivers Roster from API
  useEffect(() => {
    async function loadDrivers() {
      try {
        const res = await api.get<any>("/api/auth/users/");
        const userList = Array.isArray(res) ? res : res.results || [];
        const driverUsers = userList.filter((u: any) => u.role === "driver");
        if (driverUsers.length > 0) {
          const mapped: DriverProfile[] = driverUsers.map((u: any, idx: number) => ({
            pos: idx + 1,
            kart: String(((idx * 5 + 3) % 20) + 1),
            name: u.name || u.email,
            lapTime: "1:24.312",
            session: "Race Sim 3",
            gap: idx === 0 ? "---" : `+0.${300 + idx * 250}`,
            baseSpeed: 80 + (idx % 3) * 4,
            baseHr: 140 + idx * 5,
            baseSpo2: 97,
            baseBreathing: 22,
            stressIndex: 0.6,
            hydration: 88,
            status: "OPTIMAL",
            statusColor: "#33D17E",
            alerts: idx * 2,
            customThreshold: DEFAULT_SPRINT_CEILING,
          }));
          setDrivers(mapped);
          if (mapped[0]) setSelectedKart(mapped[0].kart);
        }
      } catch (err) {
        console.warn("Using default driver roster:", err);
      }
    }
    loadDrivers();
  }, []);

  // Fetch Historical Sessions & Active Session ID from API
  useEffect(() => {
    async function loadSessions() {
      try {
        const res = await api.get<any>("/api/sessions/");
        const sessionList = Array.isArray(res) ? res : res.results || [];
        if (sessionList.length > 0) {
          setActiveSessionId(sessionList[0].id);
          const mapped: HistoricalSession[] = sessionList.map((s: any) => ({
            id: s.id.length > 8 ? `SESS-${s.id.slice(0, 4).toUpperCase()}` : s.id,
            rawId: s.id,
            driver: s.driver_name || "—",
            kart: s.kart || "—",
            date: s.started_at ? new Date(s.started_at).toISOString().split("T")[0] : "—",
            duration: s.duration || "—",
            mode: s.mode ? s.mode.charAt(0).toUpperCase() + s.mode.slice(1) : "—",
            laps: s.laps ?? "—",
            bestLap: s.best_lap || "—",
            maxG: s.max_g || "—",
            alerts: s.alert_count ?? 0,
          }));
          setHistoricalSessions(mapped);
        }
      } catch (err) {
        console.warn("Using default historical sessions:", err);
      }
    }
    loadSessions();
  }, []);

  return {
    activeTab,
    setActiveTab,
    drivers,
    selectedKart,
    setSelectedKart,
    selectedDriver,
    thresholds,
    setThresholds,
    currentThreshold,
    sliderMin,
    sliderMax,
    currentZoneObj,
    historicalSessions,
    activeTrackId,
    rosterMap,
    ...telemetry,
    ...notesManager,
  };
}
