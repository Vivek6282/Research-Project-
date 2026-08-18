/**
 * Trackside — Coach Dashboard (Pit-Wall Coaching Console)
 *
 * Full Feature Matrix from BUILD_BRIEF.md with target Figma Design Layer:
 * - Tab Navigation: [ LIVE PIT-WALL ] & [ HISTORICAL SESSIONS ]
 * - Driver Roster & Live Timing Tower: 5-driver classification with live status (Active / PITS)
 * - Live Trajectory Feed: 20Hz streaming speed oscilloscope SVG waveform (Actual vs Target)
 * - 5-Segment LED Signal Strip: Mirroring glove status lights
 * - Live Biometric Cards: Heart Rate (142 bpm), Blood Oxygen SpO2 (97%), Breathing Rate (22 rpm)
 * - Driver Condition Panel: Stress Index (0.62), Hydration (88%), Session duration, Active alerts
 * - Per-Driver Zone Threshold Control: Custom threshold slider (e.g. Hairpin zone max 1.15g)
 * - Session Notes: Coach notes recorder tied to active driver & lap/zone
 * - Historical Session Log: Table of past academy sessions with filter & session detail modal
 * - Phase 2 Placeholder: "Development Ongoing" banner with #E8C547 accent
 */

import { useState, useEffect } from "react";
import { TopBar } from "../../components/shell/top-bar";
import { SignalStrip } from "../../components/ui/signal-strip";
import { TutorialCallout } from "../../components/ui/tutorial-callout";
import { api } from "../../lib/api";
import { startMockTelemetryEngine } from "../../lib/mockTelemetry";

const USE_MOCK_TELEMETRY = import.meta.env.VITE_USE_MOCK_TELEMETRY !== "false";


const DEFAULT_SPRINT_FLOOR = 1.0;
const DEFAULT_SPRINT_CEILING = 1.5;


interface DriverProfile {
  pos: number;
  kart: string;
  name: string;
  lapTime: string;
  session: string;
  gap: string;
  baseSpeed: number;
  baseHr: number;
  baseSpo2: number;
  baseBreathing: number;
  stressIndex: number;
  hydration: number;
  status: string;
  statusColor: string;
  alerts: number;
  customThreshold: number;
  inPit?: boolean;
}

const DRIVERS: DriverProfile[] = [
  { pos: 1, kart: "12", name: "Lucas Vance", lapTime: "1:24.312", session: "Race Sim 3", gap: "---", baseSpeed: 88, baseHr: 154, baseSpo2: 98, baseBreathing: 24, stressIndex: 0.62, hydration: 90, status: "OPTIMAL", statusColor: "#33D17E", alerts: 0, customThreshold: DEFAULT_SPRINT_CEILING },
  { pos: 2, kart: "7", name: "Lena Hartmann", lapTime: "1:24.688", session: "Qualifying 2", gap: "+0.376", baseSpeed: 84, baseHr: 162, baseSpo2: 97, baseBreathing: 26, stressIndex: 0.74, hydration: 85, status: "ELEVATED STRESS", statusColor: "#F2A93B", alerts: 2, customThreshold: 1.10 },
  { pos: 3, kart: "3", name: "Kai Nakamura", lapTime: "1:25.902", session: "Practice 1", gap: "+1.590", baseSpeed: 80, baseHr: 148, baseSpo2: 99, baseBreathing: 21, stressIndex: 0.45, hydration: 92, status: "OPTIMAL", statusColor: "#33D17E", alerts: 1, customThreshold: 1.05 },
  { pos: 4, kart: "18", name: "Marcus Brody", lapTime: "1:26.114", session: "Race Sim 3", gap: "+1.802", baseSpeed: 78, baseHr: 171, baseSpo2: 96, baseBreathing: 28, stressIndex: 0.81, hydration: 78, status: "HIGH FATIGUE", statusColor: "#E5473C", alerts: 4, customThreshold: DEFAULT_SPRINT_CEILING, inPit: true },
  { pos: 5, kart: "5", name: "Ethan Cole", lapTime: "1:26.517", session: "Practice 2", gap: "+2.205", baseSpeed: 76, baseHr: 158, baseSpo2: 97, baseBreathing: 23, stressIndex: 0.58, hydration: 88, status: "OPTIMAL", statusColor: "#33D17E", alerts: 0, customThreshold: DEFAULT_SPRINT_FLOOR },
];

interface SessionNote {
  id: string;
  timestamp: string;
  driverName: string;
  kart: string;
  zone: string;
  lap: string;
  text: string;
}

const INITIAL_NOTES: SessionNote[] = [
  { id: "n1", timestamp: "12:02:15", driverName: "Marco Ferretti", kart: "12", zone: "Turn 4 Hairpin", lap: "Lap 5", text: "Apex entry late by 0.3s. Good exit throttle control." },
  { id: "n2", timestamp: "11:58:40", driverName: "Lena Hartmann", kart: "7", zone: "Sector 2 Chicane", lap: "Lap 3", text: "G-force peak 1.42g near safety limit. Instructed tighter kerb line." },
];

const HISTORICAL_SESSIONS = [
  { id: "SESS-1092", driver: "Marco Ferretti", kart: "#12", date: "2026-08-08", duration: "42 min", mode: "Performance", laps: 28, bestLap: "1:23.104", maxG: "1.42g", alerts: 3 },
  { id: "SESS-1091", driver: "Lena Hartmann", kart: "#07", date: "2026-08-08", duration: "38 min", mode: "Performance", laps: 24, bestLap: "1:24.688", maxG: "1.38g", alerts: 5 },
  { id: "SESS-1090", driver: "Kai Nakamura", kart: "#03", date: "2026-08-07", duration: "45 min", mode: "Safety", laps: 30, bestLap: "1:25.902", maxG: "1.18g", alerts: 1 },
  { id: "SESS-1089", driver: "Ethan Cole", kart: "#05", date: "2026-08-07", duration: "30 min", mode: "Performance", laps: 18, bestLap: "1:26.517", maxG: "1.52g", alerts: 8 },
];export function CoachDashboard() {
  const [activeTab, setActiveTab] = useState<"live" | "history">("live");
  const [drivers, setDrivers] = useState<DriverProfile[]>(DRIVERS);
  const [selectedKart, setSelectedKart] = useState("12");
  const [thresholds, setThresholds] = useState<Record<string, number>>({
    "12": DEFAULT_SPRINT_CEILING, "7": 1.10, "3": 1.05, "18": DEFAULT_SPRINT_CEILING, "5": DEFAULT_SPRINT_FLOOR,
  });

  const [historicalSessions, setHistoricalSessions] = useState<any[]>(HISTORICAL_SESSIONS);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  const [activeTrackId, setActiveTrackId] = useState<string | null>(null);
  const [zones, setZones] = useState<{ id: string; label: string; corner_type?: string; threshold_g?: number; min_threshold_g?: number }[]>([
    { id: "z1", label: "Turn 4 Hairpin", corner_type: "hairpin", threshold_g: DEFAULT_SPRINT_CEILING, min_threshold_g: DEFAULT_SPRINT_FLOOR },
    { id: "z2", label: "Sector 2 Chicane", corner_type: "chicane", threshold_g: DEFAULT_SPRINT_CEILING, min_threshold_g: DEFAULT_SPRINT_FLOOR },
    { id: "z3", label: "Main Straight", corner_type: "straight", threshold_g: DEFAULT_SPRINT_CEILING, min_threshold_g: DEFAULT_SPRINT_FLOOR },
  ]);
  const [selectedZoneId, setSelectedZoneId] = useState<string>("z1");
  const [isCreatingZone, setIsCreatingZone] = useState<boolean>(false);
  const [newZoneName, setNewZoneName] = useState<string>("");
  const [newCornerType, setNewCornerType] = useState<string>("hairpin");
  const [isSavingZone, setIsSavingZone] = useState<boolean>(false);

  const [notes, setNotes] = useState<SessionNote[]>(INITIAL_NOTES);
  const [newNoteText, setNewNoteText] = useState("");

  const [rosterMap, setRosterMap] = useState<Record<string, { current_g: number; active_threshold: number; stage: string }>>({});

  const selectedDriver = drivers.find((d) => d.kart === selectedKart) || drivers[0] || DRIVERS[0];

  const currentZoneObj = zones.find((z) => z.id === selectedZoneId) || zones[0];
  const sliderMin = currentZoneObj?.min_threshold_g ?? DEFAULT_SPRINT_FLOOR;
  const sliderMax = currentZoneObj?.threshold_g ?? DEFAULT_SPRINT_CEILING;

  // Connect Safety vs Performance Mode distinction:
  // Safety Mode drivers default toward lower end (sliderMin, e.g. 1.0g); Performance Mode drivers default toward upper end (sliderMax, e.g. 1.15g).
  const selectedDriverMode = (selectedDriver?.session || "").toLowerCase().includes("safety") ? "Safety" : "Performance";
  const modeDefaultThreshold = selectedDriverMode === "Safety" ? sliderMin : sliderMax;
  const currentThreshold = thresholds[selectedKart] ?? modeDefaultThreshold;

  // Poll GET /api/sessions/roster-status/ every 2.5s for Timing Tower signal strips
  useEffect(() => {
    if (activeTab !== "live") return;

    async function fetchRosterStatus() {
      try {
        const res: any = await api.get("/api/sessions/roster-status/");
        if (res && Array.isArray(res.roster)) {
          const map: Record<string, { current_g: number; active_threshold: number; stage: string }> = {};
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

  // 1. Fetch Drivers Roster from API
  useEffect(() => {
    async function loadDrivers() {
      try {
        const res = await api.get<any>("/api/auth/users/");
        const userList = Array.isArray(res) ? res : res.results || [];
        const driverUsers = userList.filter((u: any) => u.role === "driver");
        if (driverUsers.length > 0) {
          const mapped: DriverProfile[] = driverUsers.map((u: any, idx: number) => ({
            pos: idx + 1,
            kart: String((idx * 5 + 3) % 20 + 1),
            name: u.name || u.email,
            lapTime: "1:24.312",
            session: "Race Sim 3",
            gap: idx === 0 ? "---" : `+0.${300 + idx * 250}`,
            baseSpeed: 80 + (idx % 3) * 4,
            baseHr: 140 + idx * 5,
            baseSpo2: 97,
            baseBreathing: 22,
            stressIndex: 0.60,
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

  // 2. Fetch Available Zones for Active Track from API
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
            const mappedZones = zoneList.map((z: any) => ({
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


  // 3. Fetch Historical Sessions & Active Session ID from API
  useEffect(() => {
    async function loadSessions() {
      try {
        const res = await api.get<any>("/api/sessions/");
        const sessionList = Array.isArray(res) ? res : res.results || [];
        if (sessionList.length > 0) {
          setActiveSessionId(sessionList[0].id);
          const mapped = sessionList.map((s: any) => ({
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


  // 4. Fetch Notes for Active Session from API
  useEffect(() => {
    if (!activeSessionId) return;
    async function loadNotes() {
      try {
        const res = await api.get<any>(`/api/sessions/${activeSessionId}/notes/`);
        const noteList = Array.isArray(res) ? res : res.results || [];
        if (noteList.length > 0) {
          const mapped: SessionNote[] = noteList.map((n: any) => ({
            id: n.id,
            timestamp: n.created_at ? new Date(n.created_at).toLocaleTimeString("en-GB") : new Date().toLocaleTimeString("en-GB"),
            driverName: n.coach_name || selectedDriver.name,
            kart: selectedDriver.kart,
            zone: n.zone_label || "General",
            lap: "Lap 5",
            text: n.note_text || n.text || "",
          }));
          setNotes(mapped);
        }
      } catch (err) {
        console.warn("Using default session notes:", err);
      }
    }
    loadNotes();
  }, [activeSessionId]);

  // Real-time telemetry metrics
  const [currentSpeed, setCurrentSpeed] = useState(selectedDriver.baseSpeed);
  const [currentHr, setCurrentHr] = useState(selectedDriver.baseHr);
  const [currentSpo2, setCurrentSpo2] = useState(selectedDriver.baseSpo2);
  const [currentBreathing, setCurrentBreathing] = useState(selectedDriver.baseBreathing);
  const [currentGForce, setCurrentGForce] = useState(1.42);

  // WebSocket connection status for live telemetry pipeline
  const [wsStatus, setWsStatus] = useState<"connected" | "reconnecting" | "disconnected">("disconnected");

  // Waveform oscilloscope points
  const [actualSpeedPath, setActualSpeedPath] = useState<number[]>([
    110, 105, 90, 70, 60, 65, 80, 110, 125, 130, 115, 85, 65, 75, 95, 105
  ]);
  const [targetSpeedPath] = useState<number[]>([
    100, 95, 85, 65, 55, 60, 75, 105, 120, 125, 110, 80, 60, 70, 90, 100
  ]);

  // Biometrics Sparkline History
  const [hrHistory, setHrHistory] = useState<number[]>([30, 25, 20, 15, 22, 18, 25, 20, 15, 24]);
  const [spo2History, setSpo2History] = useState<number[]>([15, 18, 22, 20, 16, 18, 22, 19, 17, 15]);
  const [breathingHistory, setBreathingHistory] = useState<number[]>([25, 28, 20, 22, 26, 24, 28, 20, 22, 25]);

  // Sector Deltas
  const s1 = 28.104;
  const s2 = 31.882;
  const s3 = 24.326;

  // Sync state when switching driver
  useEffect(() => {
    setCurrentSpeed(selectedDriver.baseSpeed);
    setCurrentHr(selectedDriver.baseHr);
    setCurrentSpo2(selectedDriver.baseSpo2);
    setCurrentBreathing(selectedDriver.baseBreathing);
  }, [selectedKart]);

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
          if (USE_MOCK_TELEMETRY) {
            // Discard incoming WebSocket packets when mock telemetry mode is enabled
            return;
          }
          try {
            const message = JSON.parse(event.data);
            if (message.type === "telemetry_reading" && message.data) {
              const { speed_kmh, lateral_g } = message.data;
              if (typeof speed_kmh === "number") {
                setCurrentSpeed(Math.round(speed_kmh));
                setActualSpeedPath((prev) => [...prev.slice(1), Math.round(speed_kmh)]);
              }
              if (typeof lateral_g === "number") {
                setCurrentGForce(Number(lateral_g.toFixed(2)));
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
    if (!USE_MOCK_TELEMETRY) return; // Do NOT run mock generator when mock mode is false

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

  // Handle Zone Selection Change in Session Notes
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

  // Handle Creating a New Zone via POST /api/tracks/<trackId>/zones/
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
          const createdZone = {
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
      console.warn("Failed creating zone via API, adding locally:", err);
    } finally {
      setIsSavingZone(false);
    }

    const localZone = {
      id: `z-${Date.now()}`,
      label: name,
      corner_type: newCornerType,
    };
    setZones((prev) => [...prev, localZone]);
    setSelectedZoneId(localZone.id);
    setIsCreatingZone(false);
    setNewZoneName("");
    return localZone;
  };

  // Handle adding session note via POST /api/sessions/<uuid>/notes/
  const handleAddNote = async () => {
    if (!newNoteText.trim()) return;

    let currentZoneId = selectedZoneId;
    if (currentZoneId === "__new__") {
      const created = await handleCreateZone();
      if (created) {
        currentZoneId = created.id;
      }
    }

    const selectedZoneObj = zones.find((z) => z.id === currentZoneId) || zones[0];
    const noteText = newNoteText.trim();

    if (activeSessionId) {
      try {
        const res = await api.post<any>(`/api/sessions/${activeSessionId}/notes/`, {
          note_text: noteText,
          zone: selectedZoneObj ? selectedZoneObj.id : undefined,
        });
        const createdNote: SessionNote = {
          id: res.id || `n-${Date.now()}`,
          timestamp: new Date().toLocaleTimeString("en-GB"),
          driverName: selectedDriver.name,
          kart: selectedDriver.kart,
          zone: selectedZoneObj ? selectedZoneObj.label : "General",
          lap: "Lap 7",
          text: noteText,
        };
        setNotes((prev) => [createdNote, ...prev]);
        setNewNoteText("");
        return;
      } catch (err) {
        console.warn("Failed posting note to API, adding locally:", err);
      }
    }

    const localNote: SessionNote = {
      id: `n-${Date.now()}`,
      timestamp: new Date().toLocaleTimeString("en-GB"),
      driverName: selectedDriver.name,
      kart: selectedDriver.kart,
      zone: selectedZoneObj ? selectedZoneObj.label : "General",
      lap: "Lap 7",
      text: noteText,
    };
    setNotes((prev) => [localNote, ...prev]);
    setNewNoteText("");
  };

  const buildSvgPath = (points: number[]) => {
    const step = 800 / (points.length - 1);
    return points.reduce((acc, y, i) => `${acc} ${i === 0 ? "M" : "L"} ${i * step} ${y}`, "");
  };

  const buildAreaPath = (points: number[]) => {
    const step = 200 / (points.length - 1);
    const linePath = points.reduce((acc, y, i) => `${acc} ${i === 0 ? "M" : "L"} ${i * step} ${y}`, "");
    return `${linePath} L 200 40 L 0 40 Z`;
  };

  return (
    <div className="min-h-screen bg-[#0A0E13] text-[#E7EDF3] select-none font-sans pb-10">
      {/* Persistent Top Navigation Bar */}
      <TopBar />

      {/* Mode Sub-Navigation Bar */}
      <div className="bg-[#12181F] border-b border-[#232B35] px-4 py-2">
        <div className="max-w-[1400px] mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2 font-mono text-xs">
            <button
              onClick={() => setActiveTab("live")}
              className={`px-3 py-1 rounded-[2px] font-bold cursor-pointer transition-all ${
                activeTab === "live"
                  ? "bg-[#3FA6E0] text-[#0A0E13]"
                  : "bg-[#161D26] text-[#7C8898] border border-[#232B35] hover:text-[#E7EDF3]"
              }`}
            >
              LIVE PIT-WALL CONSOLE
            </button>
            <button
              onClick={() => setActiveTab("history")}
              className={`px-3 py-1 rounded-[2px] font-bold cursor-pointer transition-all ${
                activeTab === "history"
                  ? "bg-[#3FA6E0] text-[#0A0E13]"
                  : "bg-[#161D26] text-[#7C8898] border border-[#232B35] hover:text-[#E7EDF3]"
              }`}
            >
              HISTORICAL SESSIONS ({historicalSessions.length})
            </button>
          </div>

          <div className="flex items-center gap-3 text-xs font-mono">
            {wsStatus === "connected" ? (
              <span className="flex items-center gap-1.5 text-[10px] text-[#33D17E] bg-[#33D17E]/10 border border-[#33D17E]/30 px-2 py-0.5 rounded-[2px] font-bold">
                <span className="w-1.5 h-1.5 rounded-full bg-[#33D17E] animate-pulse" />
                LIVE WS STREAM
              </span>
            ) : wsStatus === "reconnecting" ? (
              <span className="flex items-center gap-1.5 text-[10px] text-[#F2A93B] bg-[#F2A93B]/10 border border-[#F2A93B]/30 px-2 py-0.5 rounded-[2px] font-bold">
                <span className="w-1.5 h-1.5 rounded-full bg-[#F2A93B] animate-ping" />
                RECONNECTING WS...
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-[10px] text-[#E5473C] bg-[#E5473C]/10 border border-[#E5473C]/30 px-2 py-0.5 rounded-[2px] font-bold">
                <span className="w-1.5 h-1.5 rounded-full bg-[#E5473C]" />
                OFFLINE FALLBACK
              </span>
            )}
            <span className="text-[#7C8898]">ACADEMY TRACK:</span>
            <span className="text-[#3FA6E0] font-bold">APEX CIRCUIT NODE 7</span>
          </div>
        </div>
      </div>

      {activeTab === "live" ? (
        <>
      {/* Per-Role Dismissible Tutorial System */}
      <TutorialCallout role="coach" />

          {/* Main Pit-Wall Cockpit Grid */}
          <main className="max-w-[1400px] mx-auto px-4 py-4 grid grid-cols-12 gap-4">
            {/* Left Column (75% width): Telemetry, Biometrics & Thresholds */}
            <div className="col-span-12 lg:col-span-9 space-y-4">
              {/* LIVE TRAJECTORY Panel */}
              <div className="bg-[#12181F] border border-[#232B35] rounded-[2px] p-4">
                {/* Header & Metadata */}
                <div className="flex items-center justify-between mb-3 border-b border-[#232B35]/60 pb-2.5">
                  <div className="flex items-center gap-2 font-mono">
                    <span className="text-[#3FA6E0] font-bold">|</span>
                    <span className="text-xs font-bold uppercase tracking-wider text-[#E7EDF3]">
                      LIVE TRAJECTORY
                    </span>
                    <span className="text-xs text-[#7C8898]">
                      KART #{selectedDriver.kart} · SESSION 3 · LAP 7/12
                    </span>
                    {USE_MOCK_TELEMETRY && (
                      <span className="bg-[#F2A93B]/20 border border-[#F2A93B]/60 text-[#F2A93B] font-extrabold text-[10px] px-2 py-0.5 rounded-[2px] uppercase tracking-wider animate-pulse ml-2">
                        SIMULATED DATA — not live
                      </span>
                    )}
                  </div>
                  {/* Live Signal Indicator & Stage Label */}
                  <SignalStrip
                    currentG={currentGForce}
                    threshold={currentThreshold}
                    size="md"
                    showLabel={true}
                  />
                </div>

                {/* Readouts Row */}
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-baseline gap-1.5 font-mono">
                    <span className="text-4xl font-extrabold text-[#3FA6E0] tracking-tight">
                      {currentSpeed}
                    </span>
                    <span className="text-xs text-[#7C8898]">km/h</span>
                  </div>

                  <div className="flex items-center gap-6 font-mono text-xs">
                    <div>
                      <span className="text-[10px] text-[#7C8898] block mb-0.5">LAST</span>
                      <span className="font-semibold text-[#E7EDF3]">{selectedDriver.lapTime}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-[#7C8898] block mb-0.5">BEST</span>
                      <span className="font-semibold text-[#33D17E]">1:23.104</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-[#7C8898] block mb-0.5">DELTA</span>
                      <span className="font-semibold text-[#F2A93B]">{selectedDriver.gap}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-[#7C8898] block mb-0.5">G-FORCE</span>
                      <span className="font-semibold text-[#E7EDF3]">{currentGForce} g</span>
                    </div>
                  </div>
                </div>

                {/* Dual Waveform Speed Chart */}
                <div className="relative w-full h-[220px] bg-[#0A0E13] border border-[#232B35] rounded-[2px] p-3 overflow-hidden">
                  <div className="absolute left-2 top-2 bottom-6 flex flex-col justify-between text-[10px] font-mono text-[#4B5563]">
                    <span>140</span>
                    <span>110</span>
                    <span>80</span>
                    <span>50</span>
                    <span>20</span>
                  </div>

                  <div className="absolute left-9 top-[50%] border-b border-dashed border-[#33D17E]/50" />
                  <div className="absolute left-9 top-[4px] right-4 bottom-7">
                    <svg className="w-full h-full overflow-visible" preserveAspectRatio="none" viewBox="0 0 800 160">
                      <line x1="0" y1="0" x2="800" y2="0" stroke="#232B35" strokeDasharray="3 3" opacity="0.5" />
                      <line x1="0" y1="40" x2="800" y2="40" stroke="#232B35" strokeDasharray="3 3" opacity="0.5" />
                      <line x1="0" y1="80" x2="800" y2="80" stroke="#232B35" strokeDasharray="3 3" opacity="0.5" />
                      <line x1="0" y1="120" x2="800" y2="120" stroke="#232B35" strokeDasharray="3 3" opacity="0.5" />

                      <path
                        d={buildSvgPath(targetSpeedPath)}
                        fill="none"
                        stroke="#33D17E"
                        strokeWidth="2"
                        strokeDasharray="5 5"
                      />
                      <path
                        d={buildSvgPath(actualSpeedPath)}
                        fill="none"
                        stroke="#3FA6E0"
                        strokeWidth="2.5"
                      />
                    </svg>
                  </div>

                  <div className="absolute left-9 right-4 bottom-1 flex justify-between text-[9px] font-mono text-[#4B5563]">
                    {[1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23, 25, 27, 29, 31, 33, 35, 37, 39, 41, 43].map((num) => (
                      <span key={num}>{num}</span>
                    ))}
                  </div>

                  <div className="absolute left-10 bottom-2.5 flex items-center gap-4 text-[10px] font-mono">
                    <span className="flex items-center gap-1.5 text-[#3FA6E0]">
                      <span className="w-3 h-0.5 bg-[#3FA6E0]" /> Actual
                    </span>
                    <span className="flex items-center gap-1.5 text-[#33D17E]">
                      <span className="w-3 h-0.5 border-b border-dashed border-[#33D17E]" /> Target
                    </span>
                  </div>
                </div>
              </div>

              {/* Biometrics 3-Card Row */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {/* Heart Rate */}
                <div className="bg-[#12181F] border border-[#232B35] rounded-[2px] p-3">
                  <div className="flex items-center justify-between text-[10px] font-mono mb-2">
                    <span className="text-[#E5473C] font-bold">| HEART RATE</span>
                    <span className="text-[#7C8898]">60–190</span>
                  </div>
                  <div className="flex items-baseline gap-1 font-mono mb-2">
                    <span className="text-2xl font-extrabold text-[#E5473C]">{currentHr}</span>
                    <span className="text-[10px] text-[#7C8898]">bpm</span>
                  </div>
                  <div className="w-full h-12 bg-[#0A0E13] rounded-[1px] overflow-hidden p-1">
                    <svg className="w-full h-full" viewBox="0 0 200 40" preserveAspectRatio="none">
                      <path d={buildAreaPath(hrHistory)} fill="rgba(229, 71, 60, 0.15)" />
                      <path d={buildSvgPath(hrHistory)} fill="none" stroke="#E5473C" strokeWidth="1.5" />
                    </svg>
                  </div>
                </div>

                {/* Blood Oxygen */}
                <div className="bg-[#12181F] border border-[#232B35] rounded-[2px] p-3">
                  <div className="flex items-center justify-between text-[10px] font-mono mb-2">
                    <span className="text-[#3FA6E0] font-bold">| BLOOD OXYGEN</span>
                    <span className="text-[#7C8898]">95–100</span>
                  </div>
                  <div className="flex items-baseline gap-1 font-mono mb-2">
                    <span className="text-2xl font-extrabold text-[#3FA6E0]">{currentSpo2}</span>
                    <span className="text-[10px] text-[#7C8898]">%</span>
                  </div>
                  <div className="w-full h-12 bg-[#0A0E13] rounded-[1px] overflow-hidden p-1">
                    <svg className="w-full h-full" viewBox="0 0 200 40" preserveAspectRatio="none">
                      <path d={buildAreaPath(spo2History)} fill="rgba(63, 166, 224, 0.15)" />
                      <path d={buildSvgPath(spo2History)} fill="none" stroke="#3FA6E0" strokeWidth="1.5" />
                    </svg>
                  </div>
                </div>

                {/* Breathing */}
                <div className="bg-[#12181F] border border-[#232B35] rounded-[2px] p-3">
                  <div className="flex items-center justify-between text-[10px] font-mono mb-2">
                    <span className="text-[#33D17E] font-bold">| BREATHING</span>
                    <span className="text-[#7C8898]">12–30</span>
                  </div>
                  <div className="flex items-baseline gap-1 font-mono mb-2">
                    <span className="text-2xl font-extrabold text-[#33D17E]">{currentBreathing}</span>
                    <span className="text-[10px] text-[#7C8898]">rpm</span>
                  </div>
                  <div className="w-full h-12 bg-[#0A0E13] rounded-[1px] overflow-hidden p-1">
                    <svg className="w-full h-full" viewBox="0 0 200 40" preserveAspectRatio="none">
                      <path d={buildAreaPath(breathingHistory)} fill="rgba(51, 209, 126, 0.15)" />
                      <path d={buildSvgPath(breathingHistory)} fill="none" stroke="#33D17E" strokeWidth="1.5" />
                    </svg>
                  </div>
                </div>
              </div>

              {/* Per-Driver Per-Zone Threshold Calibration Slider Panel */}
              <div className="bg-[#12181F] border border-[#232B35] rounded-[2px] p-4">
                <div className="flex items-center justify-between mb-3 border-b border-[#232B35]/60 pb-2 font-mono">
                  <div className="flex items-center gap-2">
                    <span className="text-[#3FA6E0] font-bold">|</span>
                    <span className="text-xs font-bold text-[#E7EDF3]">CUSTOM ZONE THRESHOLD CONTROL</span>
                  </div>
                  <span className="text-[10px] text-[#3FA6E0] font-bold">
                    SERVER VALIDATED ≤ ZONE DEFAULT ({sliderMax.toFixed(2)}g)
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-center font-mono">
                  <div>
                    <div className="flex items-center justify-between text-xs mb-1.5">
                      <span className="text-[#7C8898]">ZONE: {currentZoneObj ? currentZoneObj.label.toUpperCase() : "TURN 4 HAIRPIN"}</span>
                      <span className="text-[#E7EDF3] font-bold">DRIVER: {selectedDriver.name.toUpperCase()} ({selectedDriverMode.toUpperCase()} MODE)</span>
                    </div>
                    <input
                      type="range"
                      min={sliderMin}
                      max={sliderMax}
                      step="0.05"
                      value={currentThreshold}
                      onChange={(e) => setThresholds({ ...thresholds, [selectedKart]: Number(e.target.value) })}
                      className="w-full accent-[#3FA6E0] cursor-pointer"
                    />
                    <div className="flex justify-between text-[10px] text-[#7C8898] mt-1">
                      <span>{sliderMin.toFixed(2)}g (Conservative)</span>
                      <span>{((sliderMin + sliderMax) / 2).toFixed(2)}g</span>
                      <span>{sliderMax.toFixed(2)}g (Zone Max)</span>
                    </div>
                  </div>

                  <div className="bg-[#161D26] border border-[#232B35] p-3 rounded-[2px] flex items-center justify-between">
                    <div>
                      <p className="text-[10px] text-[#7C8898]">CALIBRATED LIMIT</p>
                      <p className="text-xl font-bold text-[#3FA6E0]">{currentThreshold.toFixed(2)} g</p>
                    </div>
                    <div className="text-right">
                      <p className="text-[10px] text-[#7C8898]">SERVER STATUS</p>
                      <span className="text-[10px] text-[#33D17E] bg-[#33D17E]/10 border border-[#33D17E]/30 px-1.5 py-0.5 rounded-[1px]">
                        ✓ VALIDATED SAFE
                      </span>
                    </div>
                  </div>
                </div>
              </div>


              {/* Coach Session Notes Recorder Card */}
              <div className="bg-[#12181F] border border-[#232B35] rounded-[2px] p-4 font-mono">
                <div className="flex items-center justify-between mb-3 border-b border-[#232B35]/60 pb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[#3FA6E0] font-bold">|</span>
                    <span className="text-xs font-bold text-[#E7EDF3]">SESSION NOTES (TIED TO LAP / ZONE)</span>
                  </div>
                  <span className="text-[10px] text-[#7C8898]">ACTIVE: {selectedDriver.name} (#{selectedDriver.kart})</span>
                </div>

                <div className="space-y-2 mb-3">
                  <div className="flex gap-2">
                    <select
                      value={selectedZoneId}
                      onChange={handleZoneSelectChange}
                      className="bg-[#161D26] border border-[#232B35] text-[#E7EDF3] text-xs px-2 py-1.5 rounded-[2px] outline-none cursor-pointer"
                    >
                      {zones.map((z) => (
                        <option key={z.id} value={z.id}>
                          {z.label} {z.corner_type ? `(${z.corner_type})` : ""}
                        </option>
                      ))}
                      <option value="__new__">+ New Zone...</option>
                    </select>

                    <input
                      type="text"
                      placeholder="Record coach observation for this lap/zone..."
                      value={newNoteText}
                      onChange={(e) => setNewNoteText(e.target.value)}
                      className="flex-1 bg-[#161D26] border border-[#232B35] text-[#E7EDF3] text-xs px-3 py-1.5 rounded-[2px] outline-none focus:border-[#3FA6E0]"
                    />

                    <button
                      onClick={handleAddNote}
                      className="bg-[#3FA6E0] text-[#0A0E13] font-bold text-xs px-4 py-1.5 rounded-[2px] hover:bg-[#3FA6E0]/90 cursor-pointer"
                    >
                      SAVE NOTE
                    </button>
                  </div>

                  {/* Extensible New Zone Creation Form */}
                  {isCreatingZone && (
                    <div className="flex items-center gap-2 p-2 bg-[#161D26] border border-[#3FA6E0]/50 rounded-[2px] text-xs animate-fade-in">
                      <span className="text-[#3FA6E0] font-bold">NEW ZONE:</span>
                      <input
                        type="text"
                        placeholder="Zone Name (e.g. Turn 7 Kink)"
                        value={newZoneName}
                        onChange={(e) => setNewZoneName(e.target.value)}
                        className="bg-[#0A0E13] border border-[#232B35] text-[#E7EDF3] text-xs px-2 py-1 rounded-[2px] flex-1 outline-none focus:border-[#3FA6E0]"
                      />
                      <select
                        value={newCornerType}
                        onChange={(e) => setNewCornerType(e.target.value)}
                        className="bg-[#0A0E13] border border-[#232B35] text-[#E7EDF3] text-xs px-2 py-1 rounded-[2px] outline-none cursor-pointer"
                      >
                        <option value="hairpin">Hairpin</option>
                        <option value="sweeper">Sweeper</option>
                        <option value="chicane">Chicane</option>
                        <option value="straight">Straight</option>
                        <option value="other">Other</option>
                      </select>
                      <button
                        type="button"
                        onClick={handleCreateZone}
                        disabled={isSavingZone}
                        className="bg-[#33D17E] text-[#0A0E13] font-bold px-3 py-1 rounded-[2px] cursor-pointer hover:bg-[#33D17E]/90"
                      >
                        {isSavingZone ? "SAVING..." : "ADD ZONE"}
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setIsCreatingZone(false);
                          setSelectedZoneId(zones[0]?.id || "");
                        }}
                        className="text-[#7C8898] hover:text-[#E7EDF3] px-2 py-1 cursor-pointer"
                      >
                        CANCEL
                      </button>
                    </div>
                  )}
                </div>

                {/* Session Notes Feed */}
                <div className="space-y-1.5 max-h-32 overflow-y-auto pr-1">
                  {notes.map((n) => (
                    <div key={n.id} className="bg-[#161D26] border border-[#232B35] p-2 rounded-[2px] flex items-center justify-between text-xs">
                      <div>
                        <span className="text-[#3FA6E0] font-bold mr-2">[{n.timestamp}]</span>
                        <span className="text-[#E7EDF3] font-semibold">{n.driverName} ({n.zone}):</span>
                        <span className="text-[#7C8898] ml-1.5">{n.text}</span>
                      </div>
                      <span className="text-[10px] text-[#7C8898] bg-[#0A0E13] px-1.5 py-0.5 rounded">{n.lap}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Phase 2 Out of Scope Banner (Distinct Yellow Accent #E8C547) */}
              <div className="bg-[#12181F] border border-[#E8C547]/40 rounded-[2px] p-3 font-mono">
                <div className="flex items-center gap-2 mb-1">
                  <span className="bg-[#E8C547] text-[#0A0E13] text-[9px] font-bold px-1.5 py-0.5 rounded-[1px] uppercase">
                    DEVELOPMENT ONGOING
                  </span>
                  <span className="text-xs font-bold text-[#E8C547] uppercase">
                    PHASE 2: CROSS-DRIVER ML ANALYTICS & RISK PREDICTION
                  </span>
                </div>
                <p className="text-[11px] text-[#7C8898]">
                  Automated driving-style badges, cross-driver overlap comparisons, and plain-language telemetry advice will be activated in Phase 2 deployment.
                </p>
              </div>
            </div>

            {/* Right Column (25% width): Timing Tower & Sector Deltas */}
            <div className="col-span-12 lg:col-span-3 space-y-4">
              {/* TIMING TOWER Panel */}
              <div className="bg-[#12181F] border border-[#232B35] rounded-[2px] p-3">
                <div className="flex items-center justify-between mb-3 border-b border-[#232B35]/60 pb-2 font-mono">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-[#E7EDF3]">
                    <span className="text-[#3FA6E0]">|</span> TIMING TOWER
                  </div>
                  <div className="flex items-center gap-1 text-[10px] text-[#33D17E]">
                    <span className="text-[#7C8898]">{drivers.length}/{drivers.length} ON TRACK</span>
                    <span className="animate-pulse">• LIVE</span>
                  </div>
                </div>

                {/* Roster Classification Rows */}
                <div className="space-y-1.5 font-mono">
                  {drivers.map((d) => {
                    const isSelected = selectedKart === d.kart;
                    const rosterInfo = rosterMap[d.kart];
                    const driverG = rosterInfo ? rosterInfo.current_g : (thresholds[d.kart] ? thresholds[d.kart] * 0.7 : 0.85);
                    const driverThresh = rosterInfo ? rosterInfo.active_threshold : (thresholds[d.kart] || 1.15);

                    return (
                      <div
                        key={d.pos}
                        onClick={() => setSelectedKart(d.kart)}
                        className="p-2 rounded-[2px] flex items-center justify-between text-xs cursor-pointer transition-all duration-150"
                        style={{
                          background: isSelected ? "#161D26" : "transparent",
                          border: `1px solid ${isSelected ? "#3FA6E0" : "transparent"}`,
                          boxShadow: isSelected ? "0 0 10px rgba(63,166,224,0.15)" : "none",
                        }}
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-[#7C8898] text-[10px] w-3">{d.pos}</span>
                          <span className="w-5 h-5 rounded-[1px] bg-[#232B35] text-[#E7EDF3] text-[10px] font-bold flex items-center justify-center border border-[#3A4553]">
                            {d.kart}
                          </span>
                          <div>
                            <p className="font-semibold text-xs text-[#E7EDF3] leading-none mb-1">{d.name}</p>
                            <p className="text-[9px] text-[#7C8898] leading-none">
                              {d.lapTime} · <span className={d.inPit ? "text-[#F2A93B]" : "text-[#7C8898]"}>{d.session}</span>
                            </p>
                          </div>
                        </div>

                        <div className="flex flex-col items-end gap-1">
                          <SignalStrip
                            currentG={driverG}
                            threshold={driverThresh}
                            size="sm"
                            showLabel={false}
                          />
                          <span className="text-[#3FA6E0] text-right font-bold text-[10px]">
                            {d.gap}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* SECTOR DELTAS Panel */}

              <div className="bg-[#12181F] border border-[#232B35] rounded-[2px] p-3">
                <div className="flex items-center justify-between mb-3 border-b border-[#232B35]/60 pb-2 font-mono">
                  <span className="text-xs font-bold text-[#E7EDF3]">
                    <span className="text-[#3FA6E0]">|</span> SECTOR DELTAS
                  </span>
                  <span className="text-[9px] text-[#7C8898]">VS SESSION BEST</span>
                </div>

                <div className="space-y-3 font-mono">
                  <div>
                    <div className="flex justify-between text-[11px] mb-1">
                      <span className="text-[#7C8898]">SECTOR 1 (HAIRPIN ENTRY)</span>
                      <span className="text-[#33D17E] font-bold">{s1}s (-0.142)</span>
                    </div>
                    <div className="w-full h-1.5 bg-[#0A0E13] rounded-[1px] overflow-hidden">
                      <div className="h-full bg-[#33D17E] w-[65%]" />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-[11px] mb-1">
                      <span className="text-[#7C8898]">SECTOR 2 (MID CHICANE)</span>
                      <span className="text-[#E5473C] font-bold">{s2}s (+0.310)</span>
                    </div>
                    <div className="w-full h-1.5 bg-[#0A0E13] rounded-[1px] overflow-hidden">
                      <div className="h-full bg-[#E5473C] w-[80%]" />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-[11px] mb-1">
                      <span className="text-[#7C8898]">SECTOR 3 (FINAL APEX)</span>
                      <span className="text-[#33D17E] font-bold">{s3}s (-0.088)</span>
                    </div>
                    <div className="w-full h-1.5 bg-[#0A0E13] rounded-[1px] overflow-hidden">
                      <div className="h-full bg-[#33D17E] w-[55%]" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </main>
        </>
      ) : (
        /* HISTORICAL SESSIONS TAB */
        <main className="max-w-[1400px] mx-auto px-4 py-4 font-mono">
          <div className="bg-[#12181F] border border-[#232B35] rounded-[2px] p-4">
            <div className="flex items-center justify-between mb-4 border-b border-[#232B35]/60 pb-3">
              <div>
                <h2 className="text-sm font-bold text-[#E7EDF3]">HISTORICAL ACADEMY SESSIONS</h2>
                <p className="text-xs text-[#7C8898]">Raw session telemetry records and historical coach notes</p>
              </div>
              <span className="text-xs text-[#3FA6E0] font-bold bg-[#3FA6E0]/10 border border-[#3FA6E0]/30 px-2 py-1 rounded-[2px]">
                {historicalSessions.length} SESSIONS RECORDED
              </span>
            </div>

            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-[#232B35] text-[#7C8898]">
                  <th className="py-2 px-3">SESSION ID</th>
                  <th className="py-2 px-3">DRIVER</th>
                  <th className="py-2 px-3">KART</th>
                  <th className="py-2 px-3">DATE</th>
                  <th className="py-2 px-3">DURATION</th>
                  <th className="py-2 px-3">MODE</th>
                  <th className="py-2 px-3">BEST LAP</th>
                  <th className="py-2 px-3">MAX G</th>
                  <th className="py-2 px-3">ALERTS</th>
                </tr>
              </thead>
              <tbody>
                {historicalSessions.map((s) => (
                  <tr key={s.id} className="border-b border-[#232B35]/60 hover:bg-[#161D26]">
                    <td className="py-2.5 px-3 font-bold text-[#3FA6E0]">{s.id}</td>
                    <td className="py-2.5 px-3 text-[#E7EDF3] font-semibold">{s.driver}</td>
                    <td className="py-2.5 px-3 text-[#7C8898]">{s.kart}</td>
                    <td className="py-2.5 px-3 text-[#7C8898]">{s.date}</td>
                    <td className="py-2.5 px-3 text-[#E7EDF3]">{s.duration}</td>
                    <td className="py-2.5 px-3 text-[#33D17E]">{s.mode}</td>
                    <td className="py-2.5 px-3 text-[#E7EDF3] font-bold">{s.bestLap}</td>
                    <td className="py-2.5 px-3 text-[#F2A93B]">{s.maxG}</td>
                    <td className="py-2.5 px-3 text-[#E5473C] font-bold">{s.alerts}</td>
                  </tr>
                ))}

              </tbody>

            </table>
          </div>
        </main>
      )}
    </div>
  );
}
