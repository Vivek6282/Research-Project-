/**
 * Trackside — Driver Dashboard
 *
 * Driver Pit-Wall Telemetry Console composing:
 * - Real-time telemetry feed and glove LED status
 * - Session setup mode selector (Safety vs Performance)
 * - Zone risk heatmap breakdown (last 5 sessions)
 * - Best lap highlight and session target evaluations
 * - Future phase preview banners (alert clips, driver badges)
 */

import { Video, Award, Play } from "lucide-react";
import { TopBar } from "../../components/shell/top-bar";
import { DevBanner } from "../../components/ui/dev-banner";
import { TutorialCallout } from "../../components/ui/tutorial-callout";
import { useDriverDashboard } from "./hooks/use-driver-dashboard";
import { TelemetryPanel } from "./components/telemetry-panel";
import { ModeSelectorPanel } from "./components/mode-selector-panel";
import { ZoneHeatmapPanel } from "./components/zone-heatmap-panel";
import { BestLapTargetPanel } from "./components/best-lap-target-panel";
import { CornerTimesPanel } from "./components/corner-times-panel";
import { useAuth } from "../../lib/auth";
import { driverLabel } from "../../lib/driver-label";

export function DriverDashboard() {
  const { user } = useAuth();
  const {
    mode,
    setMode,
    currentG,
    lastSyncTime,
    zones,
    hasSessions,
    latestSession,
    loading,
    activeThreshold,
    activeZone,
  } = useDriverDashboard();

  return (
    <div className="min-h-screen bg-[#0A0E13] text-[#E7EDF3] select-none font-sans pb-10">
      <TopBar />
      <TutorialCallout role="driver" />

      <main className="max-w-6xl mx-auto px-4 py-5 space-y-4 animate-fade-in">
        {user && (
          <div data-testid="driver-header" className="text-xs font-mono font-bold text-[#E7EDF3] truncate">
            {driverLabel(user.name, user.driver_code)}
          </div>
        )}

        {/* Live Telemetry & 5-Segment Glove Signal Strip */}
        <TelemetryPanel
          currentG={currentG}
          activeThreshold={activeThreshold}
          activeZone={activeZone}
          lastSyncTime={lastSyncTime}
        />

        {/* Session Setup Mode Selector */}
        <ModeSelectorPanel mode={mode} setMode={setMode} />

        {/* Zone-by-Zone Breakdown Heatmap */}
        <ZoneHeatmapPanel
          loading={loading}
          hasSessions={hasSessions}
          zones={zones}
        />

        {/* Best Lap & Session Goal Progress */}
        <BestLapTargetPanel latestSession={latestSession} />

        {/* Time through each corner of the latest session */}
        <CornerTimesPanel sessionId={latestSession?.id ?? null} />

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
