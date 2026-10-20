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
} from "../constants";

export { DEFAULT_SPRINT_FLOOR, DEFAULT_SPRINT_CEILING };

const EMPTY_DRIVER: DriverProfile = {
  pos: 0,
  kart: "—",
  name: "—",
  lapTime: "—",
  session: "—",
  gap: "—",
  baseSpeed: 0,
  baseHr: 0,
  baseSpo2: 0,
  baseBreathing: 0,
  stressIndex: 0,
  hydration: 0,
  status: "—",
  statusColor: "#7C8898",
  alerts: 0,
  customThreshold: DEFAULT_SPRINT_CEILING,
};

export function useCoachDashboard() {
  const [activeTab, setActiveTab] = useState<"live" | "history">("live");
  const [drivers, setDrivers] = useState<DriverProfile[]>([]);
  const [driversError, setDriversError] = useState<string | null>(null);
  const [selectedKart, setSelectedKart] = useState("");
  const [thresholds, setThresholds] = useState<Record<string, number>>({});

  const [historicalSessions, setHistoricalSessions] = useState<HistoricalSession[]>([]);
  const [sessionsError, setSessionsError] = useState<string | null>(null);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [activeTrackId, setActiveTrackId] = useState<string | null>(null);
  const [rosterMap, setRosterMap] = useState<Record<string, RosterStatusItem>>({});

  const selectedDriver =
    drivers.find((d) => d.kart === selectedKart) || drivers[0] || EMPTY_DRIVER;

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
                current_g: item.current_g ?? 0,
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

  /**
   * Fetches real drivers from the API (roster-status and users) and correlates with session data.
   */
  const loadDrivers = async () => {
    try {
      setDriversError(null);
      let rosterList: any[] = [];
      let fetchSuccess = false;

      // 1. Try /api/sessions/roster-status/ (accessible by Coach and Admin)
      try {
        const rosterRes: any = await api.get("/api/sessions/roster-status/");
        if (rosterRes && Array.isArray(rosterRes.roster)) {
          rosterList = rosterRes.roster;
          fetchSuccess = true;
        }
      } catch {
        // Fall through to /api/auth/users/
      }

      // 2. Try /api/auth/users/ (accessible by Admin)
      let userList: any[] = [];
      try {
        const userRes: any = await api.get("/api/auth/users/");
        const list = Array.isArray(userRes) ? userRes : userRes?.results || [];
        userList = list.filter((u: any) => u.role === "driver");
        fetchSuccess = true;
      } catch {
        // Expected 403 for Coach
      }

      if (!fetchSuccess) {
        throw new Error("Unable to retrieve drivers from API");
      }

      // 3. Fetch sessions to associate real session name and alert counts
      let sessionList: any[] = [];
      try {
        const sessRes: any = await api.get("/api/sessions/");
        sessionList = Array.isArray(sessRes) ? sessRes : sessRes?.results || [];
      } catch {
        // non-fatal
      }

      // Build driver profiles from real API sources only
      const driversSource =
        rosterList.length > 0
          ? rosterList.map((r: any) => ({
              id: r.driver_id,
              name: r.driver_name || "—",
              kart: r.kart || "—",
              stage: r.stage,
              active_threshold: r.active_threshold,
              in_pit: r.in_pit,
            }))
          : userList.map((u: any) => ({
              id: u.id,
              name: u.name || u.email || "—",
              kart: "—",
              stage: undefined,
              active_threshold: undefined,
              in_pit: false,
            }));

      if (driversSource.length > 0) {
        const mapped: DriverProfile[] = driversSource.map((d: any, idx: number) => {
          const matchedSession = sessionList.find(
            (s: any) => s.driver_name === d.name || s.driver === d.name || s.driver_id === d.id,
          );
          const sessionName = matchedSession?.mode
            ? matchedSession.mode.charAt(0).toUpperCase() + matchedSession.mode.slice(1)
            : matchedSession?.id
            ? `SESS-${matchedSession.id.slice(0, 4).toUpperCase()}`
            : "—";

          const stage = d.stage || "nominal";
          const statusColor =
            stage === "intervene"
              ? "#E5473C"
              : stage === "monitoring"
              ? "#F2A93B"
              : stage === "nominal"
              ? "#33D17E"
              : "#7C8898";

          return {
            pos: idx + 1,
            kart: d.kart !== "—" ? d.kart : matchedSession?.kart || "—",
            name: d.name,
            lapTime: "—",
            session: sessionName,
            gap: "—",
            baseSpeed: 0,
            baseHr: 0,
            baseSpo2: 0,
            baseBreathing: 0,
            stressIndex: 0,
            hydration: 0,
            status: d.stage ? d.stage.toUpperCase() : "—",
            statusColor,
            alerts: matchedSession?.alert_count ?? 0,
            customThreshold: d.active_threshold || DEFAULT_SPRINT_CEILING,
            inPit: d.in_pit ?? false,
          };
        });

        setDrivers(mapped);
        if (mapped[0]) setSelectedKart(mapped[0].kart);
      } else {
        setDrivers([]);
        setSelectedKart("");
      }
    } catch (err) {
      console.warn("Failed loading drivers from API:", err);
      setDriversError("Failed to load driver roster. Please try again.");
      setDrivers([]);
    }
  };

  useEffect(() => {
    loadDrivers();
  }, []);

  // Fetch Historical Sessions & Active Session ID from API
  const loadSessions = async () => {
    try {
      setSessionsError(null);
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
      } else {
        setHistoricalSessions([]);
      }
    } catch (err) {
      console.warn("Failed loading sessions from API:", err);
      setSessionsError("Failed to load historical sessions. Please try again.");
      setHistoricalSessions([]);
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  return {
    activeTab,
    setActiveTab,
    drivers,
    driversError,
    retryLoadDrivers: loadDrivers,
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
    sessionsError,
    retryLoadSessions: loadSessions,
    activeTrackId,
    rosterMap,
    ...telemetry,
    ...notesManager,
  };
}
