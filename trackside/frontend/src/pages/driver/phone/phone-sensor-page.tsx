/**
 * Trackside — Phone Sensor page (Driver, Phase 2.1).
 *
 * Turns a phone fixed in the kart into a temporary kart unit: it calibrates, then sends sideways g, speed
 * and position to the driver's real-time session ten times a second. The coach sees it live; the laptop's
 * Connect bridge passes the stage on to the glove. A coaching aid, not a safety system.
 */

import { Link } from "react-router-dom";
import { Smartphone } from "lucide-react";
import { TopBar } from "../../../components/shell/top-bar";
import { Panel } from "../../../components/ui/panel";
import { usePhoneUnit } from "./use-phone-unit";
import type { RunSnapshot } from "./phone-run";

const BUTTON = "px-4 py-3 min-h-[48px] rounded text-sm font-bold cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed";

/** One labelled number. */
function Stat({ label, value, testId }: { label: string; value: string; testId: string }) {
  return (
    <div className="border border-[#232B35] bg-[#0A0E13] rounded px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider text-[#7C8898]">{label}</div>
      <div data-testid={testId} className="text-lg font-bold font-mono">{value}</div>
    </div>
  );
}

/** The live numbers and send counters. */
function RunStats({ snap }: { snap: RunSnapshot }) {
  return (
    <div className="grid grid-cols-2 gap-2">
      <Stat label="Sideways g" testId="phone-g" value={snap.lateralG === null ? "-" : `${snap.lateralG.toFixed(2)} g`} />
      <Stat label="Speed" testId="phone-speed" value={snap.speedKmh === null ? "-" : `${snap.speedKmh} km/h`} />
      <Stat label="GPS accuracy" testId="phone-accuracy" value={snap.accuracyM === null ? "No fix" : `±${Math.round(snap.accuracyM)} m`} />
      <Stat label="Sent" testId="phone-sent" value={`${snap.sent}`} />
      <Stat label="Waiting to send" testId="phone-queued" value={`${snap.queued}`} />
      <Stat label="Dropped / refused" testId="phone-dropped" value={`${snap.dropped} / ${snap.rejected}`} />
    </div>
  );
}

/** The calibration step the run is on, with its button. */
function CalibrationStep({ snap, onStill, onSkip }: { snap: RunSnapshot; onStill: () => void; onSkip: () => void }) {
  if (snap.step === "still") {
    return (
      <div className="space-y-2">
        <p className="text-sm">Step 1: fix the phone firmly in its mount, keep the kart still, then press the button.</p>
        <button data-testid="phone-calibrate-still" className={`${BUTTON} bg-[#F2A93B] text-black w-full`} disabled={snap.collecting} onClick={onStill}>
          {snap.collecting ? "Hold still…" : "Hold still and calibrate"}
        </button>
      </div>
    );
  }
  if (snap.step === "drive") {
    return (
      <div className="space-y-2">
        <p className="text-sm">Step 2: drive straight and speed up firmly. This finds which way is forward.</p>
        <button data-testid="phone-skip-forward" className={`${BUTTON} border border-[#232B35] text-[#7C8898] w-full`} onClick={onSkip}>
          Skip (no accelerometer check)
        </button>
      </div>
    );
  }
  return <p data-testid="phone-calibrated" className="text-sm text-[#3BD16F]">Calibrated. Drive normally.</p>;
}

export function PhoneSensorPage() {
  const unit = usePhoneUnit();
  const snap = unit.snapshot;

  return (
    <div className="min-h-screen bg-[#0A0E13] text-[#E7EDF3] font-sans pb-10">
      <TopBar />
      <main className="max-w-md mx-auto px-4 py-5 space-y-4">
        <Link to="/driver" className="text-xs text-[#7C8898] underline">Back to the dashboard</Link>
        <Panel title="Phone Sensor" icon={Smartphone} testId="phone-sensor-panel">
          <div className="space-y-3">
            {unit.checking && <p className="text-sm text-[#7C8898]">Looking for your real-time session…</p>}
            {!unit.checking && !unit.session && (
              <div data-testid="phone-no-session" className="space-y-2">
                <p className="text-sm">No real-time session is running for you. Ask your coach to start one.</p>
                <button className={`${BUTTON} border border-[#232B35] w-full`} onClick={unit.checkSession}>Check again</button>
              </div>
            )}
            {unit.session && (
              <p data-testid="phone-session" className="text-sm">
                Session on <strong>{unit.session.track_name ?? "this track"}</strong> (real time)
              </p>
            )}
            {unit.session && !unit.running && !snap && (
              <button data-testid="phone-start" className={`${BUTTON} bg-[#3BD16F] text-black w-full`} onClick={unit.start}>
                Start sensors
              </button>
            )}
            {snap && unit.running && <CalibrationStep snap={snap} onStill={unit.calibrateStill} onSkip={unit.skipForward} />}
            {snap?.message && <p data-testid="phone-message" className="text-xs text-[#7C8898]">{snap.message}</p>}
            {unit.error && <p role="alert" data-testid="phone-error" className="text-sm text-[#E5473C]">{unit.error}</p>}
            {snap?.stoppedMessage && <p role="alert" className="text-sm text-[#E5473C]">Sending stopped: {snap.stoppedMessage}</p>}
            {snap?.warnings.map((w) => <p key={w} role="alert" className="text-sm text-[#F2A93B]">{w}</p>)}
            {unit.pageHidden && unit.running && (
              <p role="alert" className="text-sm text-[#F2A93B]">Keep this page open and the screen on, or readings stop.</p>
            )}
            {snap && <RunStats snap={snap} />}
            {unit.running && (
              <button data-testid="phone-stop" className={`${BUTTON} bg-[#E5473C] text-white w-full`} onClick={unit.stop}>Stop</button>
            )}
            {snap && !unit.running && (
              <button data-testid="phone-save-recording" className={`${BUTTON} border border-[#232B35] w-full`} onClick={unit.saveRecording}>
                Save sensor recording (file)
              </button>
            )}
          </div>
        </Panel>
        <p className="text-[11px] text-[#7C8898]">
          A coaching aid, not a safety system. Mount the phone rigidly, keep this page open, and follow the marshals.
        </p>
      </main>
    </div>
  );
}
