/**
 * Trackside Maps — "Play demo" dialog: choose the driver, the number of laps and the pace.
 * The server checks everything again and creates the demo session; this form only collects choices.
 */

import { useState } from "react";
import { Play, X } from "lucide-react";
import { useActiveDrivers } from "../hooks/use-active-drivers";
import type { MapTrack } from "../types";

export interface PlayChoice {
  driverId: string;
  laps: number;
  pace: string;
}

interface PlayDemoDialogProps {
  map: MapTrack;
  onClose: () => void;
  /** Starts the run; resolves true when it started, false when the server refused (message shown by the caller) */
  onStart: (choice: PlayChoice) => Promise<boolean>;
  /** The server's message from the last refused start */
  serverError: string | null;
}

const PACES = [
  { id: "safe", label: "Safe: stays green" },
  { id: "edge", label: "Edge: amber at every corner" },
  { id: "over", label: "Over: red alerts at every corner" },
];
const inputClass = "bg-[#0A0E13] border border-[#232B35] rounded-[2px] px-2 py-1.5 text-xs font-mono text-[#E7EDF3] focus:border-[#3FA6E0] outline-none";

/** The dialog. */
export function PlayDemoDialog({ map, onClose, onStart, serverError }: PlayDemoDialogProps) {
  const { drivers, error: driversError, isLoading } = useActiveDrivers();
  const [driverId, setDriverId] = useState("");
  const [laps, setLaps] = useState("3");
  const [pace, setPace] = useState("safe");
  const [busy, setBusy] = useState(false);
  const lapsNumber = Number(laps);
  const lapsOk = Number.isInteger(lapsNumber) && lapsNumber >= 1 && lapsNumber <= 20;

  /** Start the run; close the dialog when the server accepted it. */
  async function handleStart() {
    setBusy(true);
    const started = await onStart({ driverId, laps: lapsNumber, pace });
    setBusy(false);
    if (started) onClose();
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-3">
      <div data-testid="play-demo-dialog" className="w-full max-w-md bg-[#12181F] border border-[#232B35] rounded-[4px] shadow-2xl text-[#E7EDF3]">
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#232B35] bg-[#161D26]">
          <span className="text-xs font-bold uppercase tracking-wider truncate">Play demo — {map.name}</span>
          <button aria-label="Close" onClick={onClose} className="text-[#7C8898] hover:text-[#E7EDF3] cursor-pointer"><X size={16} /></button>
        </div>
        <div className="p-4 flex flex-col gap-3">
          <p className="text-[11px] font-mono text-[#7C8898] leading-relaxed">
            Runs the simulator on this map as a demo session for the driver you choose. It is marked as a demo run, and the glove reacts through the bridge as usual.
          </p>
          <label className="flex flex-col gap-1 text-[11px] font-mono text-[#7C8898]">
            Driver (active drivers only)
            <select data-testid="play-driver-select" className={inputClass} value={driverId} onChange={(e) => setDriverId(e.target.value)} disabled={isLoading}>
              <option value="">{isLoading ? "Loading drivers…" : "Choose a driver"}</option>
              {drivers.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          </label>
          {driversError && <p role="alert" className="text-xs text-[#E5473C]">{driversError}</p>}
          <label className="flex flex-col gap-1 text-[11px] font-mono text-[#7C8898]">
            Laps (1 to 20)
            <input data-testid="play-laps-input" className={`${inputClass} w-24`} inputMode="numeric" value={laps} onChange={(e) => setLaps(e.target.value)} />
          </label>
          {!lapsOk && <p data-testid="play-laps-error" className="text-[11px] text-[#E5473C]">Laps must be a whole number from 1 to 20.</p>}
          <label className="flex flex-col gap-1 text-[11px] font-mono text-[#7C8898]">
            Pace
            <select data-testid="play-pace-select" className={inputClass} value={pace} onChange={(e) => setPace(e.target.value)} disabled={map.is_builtin}>
              {PACES.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
            </select>
          </label>
          {map.is_builtin && (
            <p data-testid="play-pace-note" className="text-[10px] font-mono text-[#7C8898]">
              The Demo Circuit always uses its own fixed demo pattern, so pace applies to custom maps only.
            </p>
          )}
          {serverError && <p role="alert" data-testid="play-server-error" className="text-xs text-[#E5473C] border border-[#E5473C]/40 rounded p-2">{serverError}</p>}
          <div className="flex justify-end gap-2">
            <button onClick={onClose} className="text-xs font-mono px-3 py-2 min-h-[36px] rounded-[2px] border border-[#232B35] text-[#7C8898] cursor-pointer">Cancel</button>
            <button data-testid="play-start-btn" disabled={!driverId || !lapsOk || busy} onClick={handleStart}
              className="inline-flex items-center gap-2 text-xs font-mono font-bold px-3 py-2 min-h-[36px] rounded-[2px] bg-[#33D17E] text-[#06121B] cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed">
              <Play size={14} /> {busy ? "Starting…" : "Start demo"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
