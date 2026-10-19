/**
 * Trackside Coach Dashboard — State Management & Telemetry Hook.
 * Manages driver roster, real-time WebSocket connection to backend Channels,
 * mock telemetry engine, zone threshold configurations, and session notes recording.
 */

import { useState, useEffect } from "react";
import { api } from "../../../lib/api";
import { startMockTelemetryEngine } from "../../../lib/mockTelemetry";
import {
  DriverProfile,
  SessionNote,
  HistoricalSession,
  TrackZone,
  RosterStatusItem,
} from "../types";

export const DEFAULT_SPRINT_FLOOR = 1.0;
export const DEFAULT_SPRINT_CEILING = 1.5;
export const USE_MOCK_TELEMETRY = import.meta.env.VITE_USE_MOCK_TELEMETRY !== "false";

const INITIAL_DRIVERS: DriverProfile[] = [
  { pos: 1, kart: "12", name: "Lucas Vance", lapTime: "1:24.312", session: "Race Sim 3", gap: "---", baseSpeed: 88, baseHr: 154, baseSpo2: 98, baseBreathing: 24, stressIndex: 0.62, hydration: 90, status: "OPTIMAL", statusColor: "#33D17E", alerts: 0, customThreshold: DEFAULT_SPRINT_CEILING },
  { pos: 2, kart: "7", name: "Lena Hartmann", lapTime: "1:24.688", session: "Qualifying 2", gap: "+0.376", baseSpeed: 84, baseHr: 162, baseSpo2: 97, baseBreathing: 26, stressIndex: 0.74, hydration: 85, status: "ELEVATED STRESS", statusColor: "#F2A93B", alerts: 2, customThreshold: 1.10 },
  { pos: 3, kart: "3", name: "Kai Nakamura", lapTime: "1:25.902", session: "Practice 1", gap: "+1.590", baseSpeed: 80, baseHr: 148, baseSpo2: 99, baseBreathing: 21, stressIndex: 0.45, hydration: 92, status: "OPTIMAL", statusColor: "#33D17E", alerts: 1, customThreshold: 1.05 },
  { pos: 4, kart: "18", name: "Marcus Brody", lapTime: "1:26.114", session: "Race Sim 3", gap: "+1.802", baseSpeed: 78, baseHr: 171, baseSpo2: 96, baseBreathing: 28, stressIndex: 0.81, hydration: 78, status: "HIGH FATIGUE", statusColor: "#E5473C", alerts: 4, customThreshold: DEFAULT_SPRINT_CEILING, inPit: true },
  { pos: 5, kart: "5", name: "Ethan Cole", lapTime: "1:26.517", session: "Practice 2", gap: "+2.205", baseSpeed: 76, baseHr: 158, baseSpo2: 97, baseBreathing: 23, stressIndex: 0.58, hydration: 88, status: "OPTIMAL", statusColor: "#33D17E", alerts: 0, customThreshold: DEFAULT_SPRINT_FLOOR },
];

const INITIAL_HISTORICAL_SESSIONS: HistoricalSession[] = [
  { id: "SESS-1092", driver: "Marco Ferretti", kart: "#12", date: "2026-08-08", duration: "42 min", mode: "Performance", laps: 28, bestLap: "1:23.104", maxG: "1.42g", alerts: 3 },
  { id: "SESS-1091", driver: "Lena Hartmann", kart: "#07", date: "2026-08-08", duration: "38 min", mode: "Performance", laps: 24, bestLap: "1:24.688", maxG: "1.38g", alerts: 5 },
  { id: "SESS-1090", driver: "Kai Nakamura", kart: "#03", date: "2026-08-07", duration: "45 min", mode: "Safety", laps: 30, bestLap: "1:25.902", maxG: "1.18g", alerts: 1 },
  { id: "SESS-1089", driver: "Ethan Cole", kart: "#05", date: "2026-08-07", duration: "30 min", mode: "Performance", laps: 18, bestLap: "1:26.517", maxG: "1.52g", alerts: 8 },
];

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
  const [zones, setZones] = useState<TrackZone[]>([]);
  const [selectedZoneId, setSelectedZoneId] = useState<string>("");
  const [isCreatingZone, setIsCreatingZone] = useState<boolean>(false);
  const [newZoneName, setNewZoneName] = useState<string>("");
  const [newCornerType, setNewCornerType] = useState<string>("hairpin");
  const [isSavingZone, setIsSavingZone] = useState<boolean>(false);

  const [notes, setNotes] = useState<SessionNote[]>([]);
  const [noteError, setNoteError] = useState<string | null>(null);
  const [newNoteText, setNewNoteText] = useState("");
  const [rosterMap, setRosterMap] = useState<Record<string, RosterStatusItem>>({});

  const selectedDriver =
    drivers.find((d) => d.kart === selectedKart) || drivers[0] || INITIAL_DRIVERS[0];

  const currentZoneObj = zones.find((z) => z.id === selectedZoneId) || zones[0];
  const sliderMin = currentZoneObj?.min_threshold_g ?? DEFAULT_SPRINT_FLOOR;
  const sliderMax = currentZoneObj?.threshold_g ?? DEFAULT_SPRINT_CEILING;

  const selectedDriverMode = (selectedDriver?.session || "").toLowerCase().includes("safety")
    ? "Safety"
    : "Performance";
  const modeDefaultThreshold = selectedDriverMode === "Safety" ? sliderMin : sliderMax;
  const currentThreshold = thresholds[selectedKart] ?? modeDefaultThreshold;

  // Real-time telemetry metrics
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

  // Fetch Available Zones for Active Track from API
  useEffect(() => {
    async function loadZones() {
      try {
        const tracksRes = await api.get<any>("/api/tracks/");
        const trackList = Array.isArray(tracksRes) ? tracksRes : tracksRes.results || [];
        if (trackList.length > 0) {
          const trackId = trackList[0].id;
          setActiveTrackId(trackId);
          const zonesRes = await api.get<any>(`/api/tracks/${trackId}/zones/`);
          const zoneList = Array.isArray(zonesRes) ? zonesRes : zonesRes.results || [];
          if (zoneList.length > 0) {
            const mappedZones: TrackZone[] = zoneList.map((z: any) => ({
              id: z.id,
              label: z.label || z.name || `Zone ${z.order_number || z.id}`,
              corner_type: z.corner_type || "other",
              threshold_g: typeof z.threshold_g === "number" ? z.threshold_g : DEFAULT_SPRINT_CEILING,
              min_threshold_g: typeof z.min_threshold_g === "number" ? z.min_threshold_g : DEFAULT_SPRINT_FLOOR,
            }));
            setZones(mappedZones);
            setSelectedZoneId(mappedZones[0].id);
          }
        }
      } catch (err) {
        console.warn("Using default track zones:", err);
      }
    }
    loadZones();
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

  // Fetch Notes for Active Session from API
  useEffect(() => {
    if (!activeSessionId) return;
    async function loadNotes() {
      try {
        const res = await api.get<any>(`/api/sessions/${activeSessionId}/notes/`);
        const noteList = Array.isArray(res) ? res : res.results || [];
        const mapped: SessionNote[] = noteList.map((n: any) => ({
          id: n.id,
          timestamp: n.created_at
            ? new Date(n.created_at).toLocaleTimeString("en-GB")
            : new Date().toLocaleTimeString("en-GB"),
          driverName: n.coach_name || selectedDriver.name,
          kart: selectedDriver.kart,
          zone: n.zone_label || "General",
          lap: "Lap 5",
          text: n.note_text || n.text || "",
        }));
        setNotes(mapped);
      } catch (err) {
        console.error("Failed loading session notes:", err);
      }
    }
    loadNotes();
  }, [activeSessionId, selectedDriver.name, selectedDriver.kart]);

  // Sync state when switching driver
  useEffect(() => {
    setCurrentSpeed(selectedDriver.baseSpeed);
    setCurrentHr(selectedDriver.baseHr);
    setCurrentSpo2(selectedDriver.baseSpo2);
    setCurrentBreathing(selectedDriver.baseBreathing);
  }, [selectedDriver]);

  // Real-time WebSocket connection to Django Channels backend
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

  // Isolated mock telemetry generator effect
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

  const handleZoneSelectChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    if (val === "__new__") {
      setIsCreatingZone(true);
      setSelectedZoneId("__new__");
    } else {
      setIsCreatingZone(false);
      setSelectedZoneId(val);
    }
  };

  const handleCreateZone = async () => {
    if (!newZoneName.trim()) return null;
    const name = newZoneName.trim();
    setIsSavingZone(true);
    try {
      let targetTrackId = activeTrackId;
      if (!targetTrackId) {
        const tracksRes = await api.get<any>("/api/tracks/");
        const trackList = Array.isArray(tracksRes) ? tracksRes : tracksRes.results || [];
        if (trackList.length > 0) {
          targetTrackId = trackList[0].id;
          setActiveTrackId(targetTrackId);
        }
      }

      if (targetTrackId) {
        const res: any = await api.post(`/api/tracks/${targetTrackId}/zones/`, {
          label: name,
          corner_type: newCornerType,
          threshold_g: 1.15,
        });

        if (res && res.id) {
          const createdZone: TrackZone = {
            id: res.id,
            label: res.label || name,
            corner_type: res.corner_type || newCornerType,
          };
          setZones((prev) => [...prev, createdZone]);
          setSelectedZoneId(createdZone.id);
          setIsCreatingZone(false);
          setNewZoneName("");
          return createdZone;
        }
      }
    } catch (err) {
      console.error("Failed creating zone via API:", err);
    } finally {
      setIsSavingZone(false);
    }
    return null;
  };

  const handleAddNote = async () => {
    setNoteError(null);
    if (!newNoteText.trim()) return;

    let currentZoneId = selectedZoneId;
    if (currentZoneId === "__new__") {
      const created = await handleCreateZone();
      if (created) {
        currentZoneId = created.id;
      } else {
        setNoteError("Failed to create new zone for note.");
        return;
      }
    }

    const selectedZoneObj = zones.find((z) => z.id === currentZoneId);
    const noteText = newNoteText.trim();

    if (!activeSessionId) {
      setNoteError("No active driving session available to record notes.");
      return;
    }

    try {
      const payload: any = { note_text: noteText };
      if (selectedZoneObj && selectedZoneObj.id) {
        payload.zone = selectedZoneObj.id;
      }
      const res = await api.post<any>(`/api/sessions/${activeSessionId}/notes/`, payload);
      const createdNote: SessionNote = {
        id: res.id,
        timestamp: res.created_at
          ? new Date(res.created_at).toLocaleTimeString("en-GB")
          : new Date().toLocaleTimeString("en-GB"),
        driverName: res.coach_name || selectedDriver.name,
        kart: selectedDriver.kart,
        zone: res.zone_label || (selectedZoneObj ? selectedZoneObj.label : "General"),
        lap: "Lap 7",
        text: noteText,
      };
      setNotes((prev) => [createdNote, ...prev]);
      setNewNoteText("");
    } catch (err: any) {
      setNoteError(err.message || "Failed to save note to server.");
    }
  };

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
    zones,
    selectedZoneId,
    setSelectedZoneId,
    isCreatingZone,
    setIsCreatingZone,
    newZoneName,
    setNewZoneName,
    newCornerType,
    setNewCornerType,
    isSavingZone,
    handleZoneSelectChange,
    handleCreateZone,
    notes,
    noteError,
    newNoteText,
    setNewNoteText,
    handleAddNote,
    rosterMap,
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
