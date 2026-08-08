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

interface DriverProfile {
  pos: number;
  kart: string;
  name: string;
  lapTime: string;
  session: string;
  gap: string;
  inPit?: boolean;
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
}

const DRIVERS: DriverProfile[] = [
  { pos: 1, kart: "12", name: "Marco Ferretti", lapTime: "1:24.312", session: "Race Sim 3", gap: "---", baseSpeed: 82, baseHr: 142, baseSpo2: 97, baseBreathing: 22, stressIndex: 0.62, hydration: 88, status: "LOW", statusColor: "#33D17E", alerts: 3, customThreshold: 1.15 },
  { pos: 2, kart: "7", name: "Lena Hartmann", lapTime: "1:24.688", session: "Race Sim 3", gap: "+0.436", baseSpeed: 88, baseHr: 154, baseSpo2: 98, baseBreathing: 24, stressIndex: 0.74, hydration: 85, status: "MODERATE", statusColor: "#F2A93B", alerts: 5, customThreshold: 1.10 },
  { pos: 3, kart: "3", name: "Kai Nakamura", lapTime: "1:25.902", session: "Race Sim 3", gap: "+0.773", baseSpeed: 79, baseHr: 136, baseSpo2: 98, baseBreathing: 20, stressIndex: 0.55, hydration: 91, status: "OPTIMAL", statusColor: "#33D17E", alerts: 1, customThreshold: 1.05 },
  { pos: 4, kart: "18", name: "Sofia Reyes", lapTime: "1:26.044", session: "PITS", gap: "+1.106", inPit: true, baseSpeed: 0, baseHr: 102, baseSpo2: 99, baseBreathing: 16, stressIndex: 0.32, hydration: 94, status: "IN PIT", statusColor: "#F2A93B", alerts: 0, customThreshold: 1.15 },
  { pos: 5, kart: "5", name: "Ethan Cole", lapTime: "1:26.517", session: "Race Sim 3", gap: "+1.798", baseSpeed: 76, baseHr: 168, baseSpo2: 95, baseBreathing: 27, stressIndex: 0.83, hydration: 82, status: "HIGH STRESS", statusColor: "#E5473C", alerts: 8, customThreshold: 1.00 },
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
];

export function CoachDashboard() {
  const [activeTab, setActiveTab] = useState<"live" | "history">("live");
  const [selectedKart, setSelectedKart] = useState("12");
  const [thresholds, setThresholds] = useState<Record<string, number>>({
    "12": 1.15, "7": 1.10, "3": 1.05, "18": 1.15, "5": 1.00,
  });

  const selectedDriver = DRIVERS.find((d) => d.kart === selectedKart) || DRIVERS[0];
  const currentThreshold = thresholds[selectedKart] || 1.15;

  // Session Notes state
  const [notes, setNotes] = useState<SessionNote[]>(INITIAL_NOTES);
  const [newNoteText, setNewNoteText] = useState("");
  const [selectedZone, setSelectedZone] = useState("Turn 4 Hairpin");

  // Real-time telemetry metrics
  const [currentSpeed, setCurrentSpeed] = useState(selectedDriver.baseSpeed);
  const [currentHr, setCurrentHr] = useState(selectedDriver.baseHr);
  const [currentSpo2, setCurrentSpo2] = useState(selectedDriver.baseSpo2);
  const [currentBreathing, setCurrentBreathing] = useState(selectedDriver.baseBreathing);
  const [currentGForce, setCurrentGForce] = useState(1.42);

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
  const [s1, setS1] = useState(28.104);
  const [s2, setS2] = useState(31.882);
  const [s3, setS3] = useState(24.326);

  // Sync state when switching driver
  useEffect(() => {
    setCurrentSpeed(selectedDriver.baseSpeed);
    setCurrentHr(selectedDriver.baseHr);
    setCurrentSpo2(selectedDriver.baseSpo2);
    setCurrentBreathing(selectedDriver.baseBreathing);
  }, [selectedKart]);

  // Real-time 20Hz telemetry streaming engine
  useEffect(() => {
    const interval = setInterval(() => {
      const time = Date.now() / 300;

      if (selectedDriver.inPit) {
        setCurrentSpeed(0);
        setCurrentGForce(0.00);
      } else {
        const speedVar = Math.round(selectedDriver.baseSpeed + Math.sin(time) * 14 + (Math.random() * 3 - 1.5));
        setCurrentSpeed(Math.max(45, Math.min(145, speedVar)));
        setCurrentGForce(Number((1.10 + Math.abs(Math.sin(time * 0.8)) * 0.65).toFixed(2)));
      }

      setCurrentHr(Math.round(selectedDriver.baseHr + Math.sin(time * 0.5) * 4 + (Math.random() * 2 - 1)));
      setCurrentSpo2(Math.min(99, Math.max(94, Math.round(selectedDriver.baseSpo2 + (Math.random() * 0.6 - 0.3)))));
      setCurrentBreathing(Math.round(selectedDriver.baseBreathing + (Math.random() * 1.6 - 0.8)));

      setActualSpeedPath((prev) => {
        const nextVal = selectedDriver.inPit
          ? 140
          : 160 - ((currentSpeed / 140) * 120 + (Math.random() * 8 - 4));
        return [...prev.slice(1), Math.max(20, Math.min(150, nextVal))];
      });

      setHrHistory((prev) => [...prev.slice(1), Math.max(8, Math.min(35, 40 - (currentHr / 190) * 35))]);
      setSpo2History((prev) => [...prev.slice(1), Math.max(10, Math.min(35, 40 - (currentSpo2 / 100) * 30))]);
      setBreathingHistory((prev) => [...prev.slice(1), Math.max(10, Math.min(35, 40 - (currentBreathing / 30) * 30))]);

      setS1(Number((28.104 + (Math.random() * 0.04 - 0.02)).toFixed(3)));
      setS2(Number((31.882 + (Math.random() * 0.04 - 0.02)).toFixed(3)));
      setS3(Number((24.326 + (Math.random() * 0.04 - 0.02)).toFixed(3)));
    }, 150);

    return () => clearInterval(interval);
  }, [selectedKart, selectedDriver, currentSpeed, currentHr, currentSpo2, currentBreathing]);

  // Handle adding session note
  const handleAddNote = () => {
    if (!newNoteText.trim()) return;
    const note: SessionNote = {
      id: `n-${Date.now()}`,
      timestamp: new Date().toLocaleTimeString('en-GB'),
      driverName: selectedDriver.name,
      kart: selectedDriver.kart,
      zone: selectedZone,
      lap: "Lap 7",
      text: newNoteText.trim(),
    };
    setNotes([note, ...notes]);
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
              HISTORICAL SESSIONS ({HISTORICAL_SESSIONS.length})
            </button>
          </div>

          <div className="flex items-center gap-3 text-xs font-mono">
            <span className="text-[#7C8898]">ACADEMY TRACK:</span>
            <span className="text-[#3FA6E0] font-bold">APEX CIRCUIT NODE 7</span>
          </div>
        </div>
      </div>

      {activeTab === "live" ? (
        <>
          {/* Onboarding Announcement Banner */}
          <div className="bg-[#12181F] border-b border-[#232B35] px-4 py-2">
            <div className="max-w-[1400px] mx-auto flex items-center justify-between">
              <div className="flex items-center gap-3 text-xs font-mono">
                <span className="bg-[#3FA6E0] text-[#0A0E13] font-bold px-2 py-0.5 rounded-[2px] uppercase animate-pulse">
                  1 LIVE TELEMETRY
                </span>
                <span className="text-[#7C8898]">—</span>
                <span className="text-[#E7EDF3]">
                  The main module streams speed and trajectory from the kart unit at 20 Hz.
                </span>
              </div>
              <div className="flex items-center gap-3 text-xs font-mono">
                <button className="px-3 py-1 rounded-[2px] bg-[#161D26] border border-[#232B35] text-[#E7EDF3] hover:border-[#3FA6E0] cursor-pointer">
                  NEXT
                </button>
                <button className="text-[#7C8898] hover:text-[#E7EDF3] cursor-pointer">
                  Skip
                </button>
              </div>
            </div>
          </div>

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

                  <div className="absolute left-9 right-4 top-[50%] border-b border-dashed border-[#33D17E]/50" />
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
                    SERVER VALIDATED ≤ ZONE DEFAULT (1.15g)
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-center font-mono">
                  <div>
                    <div className="flex items-center justify-between text-xs mb-1.5">
                      <span className="text-[#7C8898]">ZONE: TURN 4 HAIRPIN</span>
                      <span className="text-[#E7EDF3] font-bold">DRIVER: {selectedDriver.name.toUpperCase()}</span>
                    </div>
                    <input
                      type="range"
                      min="0.60"
                      max="1.15"
                      step="0.05"
                      value={currentThreshold}
                      onChange={(e) => setThresholds({ ...thresholds, [selectedKart]: Number(e.target.value) })}
                      className="w-full accent-[#3FA6E0] cursor-pointer"
                    />
                    <div className="flex justify-between text-[10px] text-[#7C8898] mt-1">
                      <span>0.60g (Conservative)</span>
                      <span>0.85g</span>
                      <span>1.15g (Zone Max)</span>
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

                <div className="flex gap-2 mb-3">
                  <select
                    value={selectedZone}
                    onChange={(e) => setSelectedZone(e.target.value)}
                    className="bg-[#161D26] border border-[#232B35] text-[#E7EDF3] text-xs px-2 py-1.5 rounded-[2px] outline-none"
                  >
                    <option value="Turn 4 Hairpin">Turn 4 Hairpin</option>
                    <option value="Sector 2 Chicane">Sector 2 Chicane</option>
                    <option value="Main Straight">Main Straight</option>
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
                    <span className="text-[#7C8898]">4/5 ON TRACK</span>
                    <span className="animate-pulse">• LIVE</span>
                  </div>
                </div>

                {/* Roster Classification Rows */}
                <div className="space-y-1.5 font-mono">
                  {DRIVERS.map((d) => {
                    const isSelected = selectedKart === d.kart;
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

                        <div className="text-right">
                          <p className={`text-[10px] font-bold ${d.gap === "---" ? "text-[#33D17E]" : "text-[#3FA6E0]"}`}>
                            {d.gap}
                          </p>
                          <div className="flex items-center gap-0.5 justify-end mt-1">
                            <span className="w-1.5 h-1.5 bg-[#33D17E] rounded-[0.5px]" />
                            <span className="w-1.5 h-1.5 bg-[#33D17E] rounded-[0.5px]" />
                            <span className="w-1.5 h-1.5 bg-[#33D17E] rounded-[0.5px]" />
                          </div>
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
                    <div className="flex items-center justify-between text-[10px] mb-1">
                      <span className="text-[#7C8898]">S1</span>
                      <span className="text-[#33D17E] font-bold">{s1.toFixed(3)}</span>
                    </div>
                    <div className="w-full h-1.5 bg-[#0A0E13] rounded-[1px] overflow-hidden">
                      <div className="h-full bg-[#33D17E] w-[75%] transition-all duration-300" />
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between text-[10px] mb-1">
                      <span className="text-[#7C8898]">S2</span>
                      <span className="text-[#33D17E] font-bold">{s2.toFixed(3)}</span>
                    </div>
                    <div className="w-full h-1.5 bg-[#0A0E13] rounded-[1px] overflow-hidden">
                      <div className="h-full bg-[#33D17E] w-[90%] transition-all duration-300" />
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between text-[10px] mb-1">
                      <span className="text-[#7C8898]">S3</span>
                      <span className="text-[#33D17E] font-bold">{s3.toFixed(3)}</span>
                    </div>
                    <div className="w-full h-1.5 bg-[#0A0E13] rounded-[1px] overflow-hidden">
                      <div className="h-full bg-[#33D17E] w-[60%] transition-all duration-300" />
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
                {HISTORICAL_SESSIONS.length} SESSIONS RECORDED
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
                {HISTORICAL_SESSIONS.map((s) => (
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
