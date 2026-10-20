/**
 * Trackside — Coach Dashboard (Pit-Wall Coaching Console)
 *
 * Full Pit-Wall Cockpit Composing:
 * - Tab Navigation: [ LIVE PIT-WALL ] & [ HISTORICAL SESSIONS ]
 * - Timing Tower Classification & Per-Driver Glove Signal Strip
 * - Live Trajectory Waveform Oscillogram (Actual vs Target)
 * - Live Track Map GPS Projection
 * - Biometrics 3-Card Row (Heart Rate, SpO2, Breathing)
 * - Custom Zone Threshold Slider & Safety Validation
 * - Session Notes Tied to Lap / Zone
 * - Historical Academy Sessions Archive
 */

import { TopBar } from "../../components/shell/top-bar";
import { LiveTrackView } from "../../components/ui/live-track-view";
import { TutorialCallout } from "../../components/ui/tutorial-callout";
import { useCoachDashboard } from "./hooks/use-coach-dashboard";
import { LiveTrajectoryPanel } from "./components/live-trajectory-panel";
import { BiometricsCards } from "./components/biometrics-cards";
import { ThresholdControlPanel } from "./components/threshold-control-panel";
import { SessionNotesPanel } from "./components/session-notes-panel";
import { TimingTowerPanel } from "./components/timing-tower-panel";
import { SectorDeltasPanel } from "./components/sector-deltas-panel";
import { HistoricalSessionsTab } from "./components/historical-sessions-tab";

export function CoachDashboard() {
  const {
    activeTab,
    setActiveTab,
    drivers,
    driversError,
    retryLoadDrivers,
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
    retryLoadSessions,
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
    currentGForce,
    currentGpsLat,
    currentGpsLng,
    wsStatus,
    actualSpeedPath,
  } = useCoachDashboard();

  return (
    <div className="min-h-screen bg-[#0A0E13] text-[#E7EDF3] select-none font-sans pb-10">
      {/* Persistent Top Navigation Bar */}
      <TopBar />

      {/* Mode Sub-Navigation Bar */}
      <div className="bg-[#12181F] border-b border-[#232B35] px-3 sm:px-4 py-2">
        <div className="max-w-[1400px] mx-auto flex flex-wrap items-center justify-between gap-2 sm:gap-4">
          <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 font-mono text-xs">
            <button
              data-testid="coach-tab-live"
              onClick={() => setActiveTab("live")}
              className={`px-2.5 sm:px-3 py-1 rounded-[2px] font-bold cursor-pointer transition-all text-[11px] sm:text-xs ${
                activeTab === "live"
                  ? "bg-[#3FA6E0] text-[#0A0E13]"
                  : "bg-[#161D26] text-[#7C8898] border border-[#232B35] hover:text-[#E7EDF3]"
              }`}
            >
              LIVE PIT-WALL CONSOLE
            </button>
            <button
              data-testid="coach-tab-history"
              onClick={() => setActiveTab("history")}
              className={`px-2.5 sm:px-3 py-1 rounded-[2px] font-bold cursor-pointer transition-all text-[11px] sm:text-xs ${
                activeTab === "history"
                  ? "bg-[#3FA6E0] text-[#0A0E13]"
                  : "bg-[#161D26] text-[#7C8898] border border-[#232B35] hover:text-[#E7EDF3]"
              }`}
            >
              HISTORICAL ({historicalSessions.length})
            </button>
          </div>

          <div className="flex flex-wrap items-center gap-2 sm:gap-3 text-xs font-mono">
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
            <div className="flex items-center gap-1 text-[11px] sm:text-xs truncate max-w-[180px] sm:max-w-none">
              <span className="text-[#7C8898] hidden md:inline">ACADEMY TRACK:</span>
              <span className="text-[#3FA6E0] font-bold truncate">APEX CIRCUIT NODE 7</span>
            </div>
          </div>
        </div>
      </div>

      {activeTab === "live" ? (
        <>
          {/* Per-Role Dismissible Tutorial System */}
          <TutorialCallout role="coach" />

          {/* Main Pit-Wall Cockpit Grid */}
          <main className="max-w-[1400px] mx-auto px-2.5 sm:px-4 py-3 sm:py-4 grid grid-cols-12 gap-3 sm:gap-4">
            {/* Main content column (75% on desktop) */}
            <div className="col-span-12 lg:col-span-9 grid grid-cols-1 gap-3 sm:gap-4">
              {/* LIVE TRAJECTORY Panel */}
              <LiveTrajectoryPanel
                selectedDriver={selectedDriver}
                currentGForce={currentGForce}
                currentThreshold={currentThreshold}
                currentSpeed={currentSpeed}
                actualSpeedPath={actualSpeedPath}
              />

              {/* LIVE TRACK VIEW Panel */}
              <LiveTrackView
                trackId={activeTrackId}
                gpsLat={currentGpsLat}
                gpsLng={currentGpsLng}
                currentG={currentGForce}
                threshold={currentThreshold}
              />

              {/* BIOMETRICS 3-Card Row */}
              <BiometricsCards />

              {/* CUSTOM ZONE THRESHOLD CONTROL Panel */}
              <ThresholdControlPanel
                currentZoneObj={currentZoneObj}
                selectedDriver={selectedDriver}
                selectedKart={selectedKart}
                sliderMin={sliderMin}
                sliderMax={sliderMax}
                currentThreshold={currentThreshold}
                thresholds={thresholds}
                setThresholds={setThresholds}
              />

              {/* SESSION NOTES Panel */}
              <SessionNotesPanel
                selectedDriver={selectedDriver}
                selectedZoneId={selectedZoneId}
                zones={zones}
                handleZoneSelectChange={handleZoneSelectChange}
                newNoteText={newNoteText}
                setNewNoteText={setNewNoteText}
                handleAddNote={handleAddNote}
                noteError={noteError}
                isCreatingZone={isCreatingZone}
                setIsCreatingZone={setIsCreatingZone}
                setSelectedZoneId={setSelectedZoneId}
                newZoneName={newZoneName}
                setNewZoneName={setNewZoneName}
                newCornerType={newCornerType}
                setNewCornerType={setNewCornerType}
                handleCreateZone={handleCreateZone}
                isSavingZone={isSavingZone}
                notes={notes}
              />

              {/* DEVELOPMENT ONGOING Banner */}
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

            {/* Sidebar column (25% on desktop) */}
            <div
              data-testid="coach-sidebar-column"
              className="col-span-12 lg:col-span-3 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-1 gap-3 sm:gap-4"
            >
              {/* TIMING TOWER Panel */}
              <TimingTowerPanel
                drivers={drivers}
                selectedKart={selectedKart}
                setSelectedKart={setSelectedKart}
                rosterMap={rosterMap}
                thresholds={thresholds}
                driversError={driversError}
                onRetry={retryLoadDrivers}
              />

              {/* SECTOR DELTAS Panel */}
              <SectorDeltasPanel />
            </div>
          </main>
        </>
      ) : (
        /* HISTORICAL SESSIONS TAB */
        <HistoricalSessionsTab
          historicalSessions={historicalSessions}
          sessionsError={sessionsError}
          onRetry={retryLoadSessions}
        />
      )}
    </div>
  );
}
