/**
 * Trackside Coach — start or finish a real-time session fed by the driver's phone (Phase 2.1).
 * The driver then opens Phone sensor on the phone fixed in the kart.
 */

import { useState } from "react";
import { Smartphone } from "lucide-react";
import { useActiveDrivers } from "../../maps/hooks/use-active-drivers";
import { useRealTimeSessions } from "../hooks/use-real-time-sessions";

const FIELD = "w-full px-3 py-2 rounded text-xs bg-[#0A0E13] border border-[#232B35] text-[#E7EDF3]";
const BUTTON = "px-3 py-2 min-h-[40px] rounded text-xs font-bold cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed";
const FLAG_TEXT: Record<string, string> = {
  mount_moved: "phone moved in its mount",
  sensor_disagreement: "motion sensors disagreed",
};

interface RealTimeSessionPanelProps {
  onWatchLive: (driverId: string) => void;
}

/** The panel: a start form and the list of running real-time sessions. */
export function RealTimeSessionPanel({ onWatchLive }: RealTimeSessionPanelProps) {
  const { drivers } = useActiveDrivers();
  const live = useRealTimeSessions();
  const [driverId, setDriverId] = useState("");
  const [trackId, setTrackId] = useState("");

  return (
    <section data-testid="real-time-panel" className="border border-[#232B35] rounded p-3 space-y-3">
      <h3 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[#F2A93B]">
        <Smartphone size={14} /> Real-time session (phone)
      </h3>
      <p className="text-[11px] text-[#7C8898]">
        For a real kart: the driver's phone sends the data. Pick a map with a GPS outline (imported or drawn).
        The driver needs consent recorded by the admin.
      </p>
      <div className="grid sm:grid-cols-3 gap-2">
        <select data-testid="real-time-driver" className={FIELD} value={driverId} onChange={(e) => setDriverId(e.target.value)}>
          <option value="">Choose a driver</option>
          {drivers.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
        <select data-testid="real-time-map" className={FIELD} value={trackId} onChange={(e) => setTrackId(e.target.value)}>
          <option value="">{live.maps.length ? "Choose a GPS map" : "No GPS maps yet"}</option>
          {live.maps.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
        </select>
        <button data-testid="real-time-start" className={`${BUTTON} bg-[#3BD16F] text-black`} disabled={!driverId || !trackId || live.busy}
          onClick={async () => (await live.start(driverId, trackId)) && onWatchLive(driverId)}>
          Start real-time session
        </button>
      </div>
      {live.error && <p role="alert" className="text-xs text-[#E5473C]">{live.error}</p>}
      {live.sessions.map((s) => (
        <div key={s.id} data-testid="real-time-row" className="flex flex-wrap items-center gap-2 text-xs border-t border-[#232B35] pt-2">
          <span className="font-bold">{s.driver_name}</span>
          <span className="text-[#7C8898]">{s.track_name} · since {new Date(s.started_at).toLocaleTimeString()}</span>
          {(s.sensor_flags ?? []).map((f) => (
            <span key={f} className="text-[#F2A93B]">⚠ {FLAG_TEXT[f] ?? f}</span>
          ))}
          <span className="ml-auto flex gap-2">
            <button className={`${BUTTON} border border-[#232B35]`} onClick={() => onWatchLive(s.driver)}>Watch live</button>
            <button data-testid="real-time-finish" className={`${BUTTON} bg-[#E5473C] text-white`} disabled={live.busy}
              onClick={() => live.finish(s.id)}>Finish</button>
          </span>
        </div>
      ))}
    </section>
  );
}
