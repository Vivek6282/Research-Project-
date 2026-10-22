/**
 * Trackside Coach Dashboard — State Management Coordinator Hook.
 * Manages driver roster, threshold calibration, and composes telemetry and notes hooks.
 */

import { useState, useEffect } from "react";
import { api } from "../../../lib/api";
import { useCoachTelemetry } from "./use-coach-telemetry";
import { useCoachNotes } from "./use-coach-notes";
import { useCoachTab } from "./use-coach-tab";
import { useActiveSession } from "./use-active-session";
import {
  DriverProfile,
  RosterStatusItem,
} from "../types";
import {
  DEFAULT_SPRINT_FLOOR,
  DEFAULT_SPRINT_CEILING,
} from "../constants";

export { DEFAULT_SPRINT_FLOOR, DEFAULT_SPRINT_CEILING };

const EMPTY_DRIVER: DriverProfile = {
  id: "",
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
  status: "NO DATA",
  statusColor: "#7C8898",
  alerts: 0,
  customThreshold: null,
};

export function useCoachDashboard() {
  const { activeTab, setActiveTab } = useCoachTab();
  const [drivers, setDrivers] = useState<DriverProfile[]>([]);
  const [driversError, setDriversError] = useState<string | null>(null);
  const [selectedDriverId, setSelectedDriverId] = useState("");
  const [thresholds, setThresholds] = useState<Record<string, number>>({});

  const [rosterMap, setRosterMap] = useState<Record<string, RosterStatusItem>>({});

  const selectedDriver =
    drivers.find((d) => d.id === selectedDriverId) || drivers[0] || EMPTY_DRIVER;

  // The session being watched: newest of the selected driver, with its own track
  const {
    historicalSessions, sessionsError, retryLoadSessions, activeSessionId, activeTrackId, activeTrackName,
  } = useActiveSession(selectedDriver.id, rosterMap[selectedDriver.id], activeTab);

  // Compose telemetry hook
  const telemetry = useCoachTelemetry(selectedDriver, activeSessionId);

  // Compose notes & zones hook
  const notesManager = useCoachNotes(
    activeSessionId,
    activeTrackId,
    selectedDriver,
  );

  const currentZoneObj =
    notesManager.zones.find((z) => z.id === notesManager.selectedZoneId) || notesManager.zones[0];
  const sliderMin = currentZoneObj?.min_threshold_g ?? DEFAULT_SPRINT_FLOOR;
  const sliderMax = currentZoneObj?.threshold_g ?? DEFAULT_SPRINT_CEILING;

  const currentThreshold = thresholds[selectedDriver.id] ?? (selectedDriver?.customThreshold ?? (currentZoneObj?.threshold_g ?? null));

  // Poll GET /api/sessions/roster-status/ every 2.5s for Timing Tower signal strips
  useEffect(() => {
    if (activeTab !== "live") return;

    async function fetchRosterStatus() {
      try {
        const res: any = await api.get("/api/sessions/roster-status/");
        if (res && Array.isArray(res.roster)) {
          const map: Record<string, RosterStatusItem> = {};
          res.roster.forEach((item: any) => {
            if (item.driver_id) {
              map[item.driver_id] = {
                current_g: item.current_g ?? null,
                active_threshold: item.active_threshold ?? null,
                stage: item.stage || "no_data",
                live: item.live ?? false,
                session_state: item.session_state || "none",
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
              driver_code: r.driver_code ?? null,
              stage: r.stage,
              active_threshold: r.active_threshold,
              session_state: r.session_state,
            }))
          : userList.map((u: any) => ({
              id: u.id,
              name: u.name || u.email || "—",
              stage: "no_data",
              active_threshold: null,
              session_state: "none",
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

          const stage = d.stage || "no_data";
          const statusColor =
            stage === "intervene"
              ? "#E5473C"
              : stage === "monitoring"
              ? "#F2A93B"
              : stage === "nominal"
              ? "#33D17E"
              : "#7C8898";

          return {
            id: d.id,
            pos: idx + 1,
            kart: "—",
            name: d.name,
            driverCode: d.driver_code ?? null,
            lapTime: "—",
            session: sessionName,
            gap: "—",
            baseSpeed: 0,
            baseHr: 0,
            baseSpo2: 0,
            baseBreathing: 0,
            stressIndex: 0,
            hydration: 0,
            status: stage !== "no_data" ? stage.toUpperCase() : "NO DATA",
            statusColor,
            alerts: matchedSession?.alert_count ?? 0,
            customThreshold: d.active_threshold ?? null,
            inPit: d.session_state === "ended",
          };
        });

        setDrivers(mapped);
        if (mapped[0]) setSelectedDriverId(mapped[0].id);
      } else {
        setDrivers([]);
        setSelectedDriverId("");
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

  const selectedDriverTrack = activeTrackName || "No active track";

  return {
    activeTab,
    setActiveTab,
    drivers,
    driversError,
    retryLoadDrivers: loadDrivers,
    selectedDriverId,
    setSelectedDriverId,
    selectedKart: selectedDriverId,
    setSelectedKart: setSelectedDriverId,
    selectedDriver,
    selectedDriverTrack,
    thresholds,
    setThresholds,
    currentThreshold,
    sliderMin,
    sliderMax,
    currentZoneObj,
    historicalSessions,
    sessionsError,
    retryLoadSessions,
    activeSessionId, activeTrackId,
    rosterMap,
    ...telemetry,
    ...notesManager,
  };
}
