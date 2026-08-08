/**
 * Trackside — Driver Dashboard
 *
 * Driver Pit-Wall Telemetry Console:
 * - Session setup mode selector (Safety Mode vs Performance Mode)
 * - Live Trajectory Telemetry & 5-Segment Glove Signal Strip (Nominal / Monitoring / Intervene)
 * - Zone-by-zone alert count breakdown (last 5 sessions)
 * - Cleanest lap highlight & session goal evaluation
 * - Phase 1.5 alert video clip player placeholder
 * - Phase 2 coaching guidance & driver longevity badges
 */

import { useState, useEffect } from "react";
import { Flag, Gauge, Trophy, Target, Video, Award, Play, Activity } from "lucide-react";
import { TopBar } from "../../components/shell/top-bar";
import { Panel } from "../../components/ui/panel";
import { DevBanner } from "../../components/ui/dev-banner";
import { SignalStrip } from "../../components/ui/signal-strip";

const ZONES = [
  { name: "Hairpin", count: 6, status: "High Risk", color: "#E5473C", threshold: 1.15 },
  { name: "Sweeper", count: 0, status: "Clean", color: "#33D17E", threshold: 1.25 },
  { name: "Chicane", count: 2, status: "Caution", color: "#F2A93B", threshold: 1.10 },
];

export function DriverDashboard() {
  const [mode, setMode] = useState<"safety" | "performance">("safety");
  const [currentG, setCurrentG] = useState(0.85);
  const activeThreshold = 1.15; // Hairpin Zone Threshold

  // Simulate real-time driver G-Force telemetry streaming
  useEffect(() => {
    const interval = setInterval(() => {
      const time = Date.now() / 400;
      // Oscillate G-force across Nominal (<0.94g), Monitoring (0.94g-1.15g), and Intervene (≥1.15g)
      const simG = Number((0.75 + Math.abs(Math.sin(time)) * 0.48).toFixed(2));
      setCurrentG(simG);
    }, 200);
    return () => clearInterval(interval);
  }, []);


  return (
    <div className="min-h-screen bg-[#0A0E13] text-[#E7EDF3] select-none font-sans pb-10">
      <TopBar />

      <main className="max-w-6xl mx-auto px-4 py-5 space-y-4 animate-fade-in">
        {/* Live Telemetry & 5-Segment Glove Signal Strip Panel */}
        <Panel title="Live Driver Telemetry & Glove LED Feed" icon={Activity}>
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-3 bg-[#161D26] border border-[#232B35] rounded-[2px] font-mono">
            <div>
              <p className="text-[10px] text-[#7C8898] uppercase">Active Zone: Turn 4 Hairpin</p>
              <div className="flex items-baseline gap-2 mt-0.5">
                <span className="text-3xl font-extrabold text-[#3FA6E0]">{currentG} g</span>
                <span className="text-xs text-[#7C8898]">/ {activeThreshold.toFixed(2)} g THRESHOLD</span>
              </div>
            </div>

            {/* Synchronized 5-Segment Signal Strip & Status Label */}
            <div className="flex flex-col items-start sm:items-end gap-1">
              <span className="text-[10px] text-[#7C8898] uppercase">GLOVE LED HARDWARE STATUS</span>
              <SignalStrip
                currentG={currentG}
                threshold={activeThreshold}
                size="lg"
                showLabel={true}
              />
            </div>
          </div>
        </Panel>

        {/* Session Setup Mode Selector */}
        <Panel title="Session Mode Setup" icon={Flag}>
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="flex gap-2 font-mono">
              <button
                onClick={() => setMode("safety")}
                className="text-xs font-mono font-bold px-4 py-2 rounded transition-all duration-150 cursor-pointer"
                style={{
                  background: mode === "safety" ? "#3FA6E0" : "transparent",
                  color: mode === "safety" ? "#06121B" : "#7C8898",
                  border: `1px solid ${mode === "safety" ? "#3FA6E0" : "#232B35"}`,
                  boxShadow: mode === "safety" ? "0 0 12px rgba(63,166,224,0.3)" : "none",
                }}
              >
                SAFETY MODE
              </button>
              <button
                onClick={() => setMode("performance")}
                className="text-xs font-mono font-bold px-4 py-2 rounded transition-all duration-150 cursor-pointer"
                style={{
                  background: mode === "performance" ? "#3FA6E0" : "transparent",
                  color: mode === "performance" ? "#06121B" : "#7C8898",
                  border: `1px solid ${mode === "performance" ? "#3FA6E0" : "#232B35"}`,
                  boxShadow: mode === "performance" ? "0 0 12px rgba(63,166,224,0.3)" : "none",
                }}
              >
                PERFORMANCE MODE
              </button>
            </div>

            <span className="text-xs font-mono text-[#7C8898]">
              Active Focus:{" "}
              <span className="text-[#3FA6E0] font-bold uppercase">
                {mode} Focus
              </span>
            </span>
          </div>
        </Panel>

        {/* Zone-by-Zone Breakdown Cards */}
        <Panel title="Zone Risk Heatmap (Last 5 Sessions)" icon={Gauge}>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {ZONES.map((z) => (
              <div
                key={z.name}
                className="rounded-lg p-3.5 text-center flex flex-col items-center justify-between border transition-all duration-150"
                style={{
                  background: "#161D26",
                  borderColor: `${z.color}33`,
                  boxShadow: `0 4px 15px ${z.color}10`,
                }}
              >
                <span
                  className="text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded mb-2"
                  style={{
                    color: z.color,
                    border: `1px solid ${z.color}44`,
                    background: `${z.color}14`,
                  }}
                >
                  {z.status}
                </span>

                <p
                  className="text-3xl font-mono font-bold my-1"
                  style={{ color: z.color }}
                >
                  {z.count}
                </p>

                <p className="text-xs font-mono text-[#7C8898]">
                  {z.name} Exceedances
                </p>
              </div>
            ))}
          </div>
        </Panel>

        {/* Best Lap & Session Goal Progress */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Panel title="Best Lap Highlight (Raw Telemetry)" icon={Trophy}>
            <div className="space-y-1 font-mono">
              <div className="flex items-baseline justify-between">
                <span className="text-2xl font-mono font-bold text-[#33D17E]">
                  48.32s
                </span>
                <span className="text-xs font-mono text-[#7C8898]">LAP 6</span>
              </div>
              <p className="text-xs text-[#7C8898]">
                Cleanest lap of the session — zero threshold exceedances recorded.
              </p>
            </div>
          </Panel>

          <Panel title="Session Target Evaluation" icon={Target}>
            <div className="space-y-1 font-mono">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-[#E7EDF3] font-bold">
                  Zero Red Alerts at Hairpin
                </span>
                <span className="text-xs font-mono font-bold text-[#E5473C] px-2 py-0.5 rounded border border-[#E5473C44] bg-[#E5473C14]">
                  NOT MET
                </span>
              </div>
              <p className="text-xs text-[#7C8898]">
                2 red alerts triggered in Hairpin zone during session.
              </p>
            </div>
          </Panel>
        </div>

        {/* Phase 1.5 Dev Banner — Alert Clips */}
        <DevBanner phase="Phase 1.5">
          <div className="flex items-center gap-2 mb-2 font-mono">
            <Video size={14} style={{ color: "#E8C547" }} />
            <p className="text-xs font-mono uppercase tracking-widest text-[#E8C547] font-bold">
              Alert Clip Sync (Rolling Buffer Video)
            </p>
          </div>
          <p className="text-xs text-[#7C8898] mb-3">
            A synchronized 10-second rolling-buffer video clip will play here for every g-force alert, linked directly to the sensor timestamp.
          </p>
          <div
            className="w-full h-28 rounded-lg flex items-center justify-center gap-2 text-xs font-mono border border-dashed border-[#232B35]"
            style={{ background: "#0A0E13", color: "#4B5563" }}
          >
            <Play size={16} />
            <span>▶ REPLAY CLIP — Hairpin (Lap 4, 1.28g)</span>
          </div>
        </DevBanner>

        {/* Phase 2 Dev Banner — Driver Badges & Trends */}
        <DevBanner phase="Phase 2">
          <div className="flex items-center gap-2 mb-2 font-mono">
            <Award size={14} style={{ color: "#E8C547" }} />
            <p className="text-xs font-mono uppercase tracking-widest text-[#E8C547] font-bold">
              Coaching Guidance, Longevity Graph & Driving Badges
            </p>
          </div>
          <p className="text-xs text-[#7C8898]">
            Automated coaching recommendations, the 5-session Career Longevity graph, driving style badges, and leaderboard will unlock when the ML model is connected.
          </p>
        </DevBanner>
      </main>
    </div>
  );
}
