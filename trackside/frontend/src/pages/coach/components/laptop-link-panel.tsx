/**
 * Trackside Coach — "Connect laptop" panel.
 * For a hosted site: the glove only talks to the bridge on a laptop, so the laptop's simulator drives the
 * glove AND posts its readings here. Pick a driver, press Start, paste the lines into the laptop's
 * demo/.env, run the simulator, then Watch live.
 */

import { useState } from "react";
import { Eye, Laptop, Square } from "lucide-react";
import { useActiveDrivers } from "../../maps/hooks/use-active-drivers";
import { envLines, useLaptopLink } from "../hooks/use-laptop-link";

interface LaptopLinkPanelProps {
  onWatchLive: (driverId: string) => void;
}

const button = "inline-flex items-center gap-1.5 text-[11px] font-mono px-3 py-1.5 min-h-[34px] rounded-[2px] border cursor-pointer";
const STATE_TEXT: Record<string, string> = {
  idle: "No link",
  waiting: "Waiting for the laptop to send readings…",
  receiving: "Receiving readings from the laptop",
  quiet: "The laptop has stopped sending readings",
};

export function LaptopLinkPanel({ onWatchLive }: LaptopLinkPanelProps) {
  const { drivers, isLoading } = useActiveDrivers();
  const { link, status, error, busy, start, stop } = useLaptopLink();
  const [driverId, setDriverId] = useState("");
  const [showToken, setShowToken] = useState(false);
  const [copied, setCopied] = useState(false);
  const active = status.state !== "idle";

  // Copy the .env lines (with the real token) to the clipboard
  async function copyLines() {
    if (!link) return;
    try {
      await navigator.clipboard.writeText(envLines(link));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setShowToken(true); // the browser refused: show the text so it can be copied by hand
    }
  }

  return (
    <div data-testid="laptop-link-panel" className="flex flex-col gap-2 p-3 rounded border border-[#232B35] bg-[#161D26]">
      <div className="flex items-center gap-2 text-xs font-mono font-bold text-[#E7EDF3]">
        <Laptop size={14} className="text-[#3FA6E0]" /> CONNECT LAPTOP (glove demo with this site)
      </div>
      <p className="text-[11px] font-mono text-[#7C8898]">
        The glove works through the bridge on your laptop. The laptop's simulator drives the glove and sends the same readings here, so this site shows the run live.
      </p>

      {!active && (
        <div className="flex flex-wrap items-center gap-2">
          <select
            data-testid="laptop-link-driver"
            value={driverId}
            onChange={(e) => setDriverId(e.target.value)}
            disabled={isLoading}
            className="px-2 py-1.5 rounded text-xs font-mono bg-[#0A0E13] border border-[#232B35] text-[#E7EDF3]"
          >
            <option value="">{isLoading ? "Loading drivers…" : "Choose a driver"}</option>
            {drivers.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
          <button
            data-testid="laptop-link-start"
            disabled={!driverId || busy}
            onClick={() => start(driverId)}
            className={`${button} border-[#3FA6E0] text-[#3FA6E0] ${!driverId || busy ? "opacity-40 cursor-not-allowed" : ""}`}
          >
            Start link
          </button>
        </div>
      )}

      {active && (
        <p data-testid="laptop-link-state" className="text-xs font-mono font-bold text-[#33D17E]">
          {STATE_TEXT[status.state]}{status.driver_name ? ` · ${status.driver_name}` : ""}
          {typeof status.readings === "number" ? ` · ${status.readings} readings` : ""}
        </p>
      )}

      {link && (
        <div className="flex flex-col gap-2">
          <p className="text-[11px] font-mono text-[#F2A93B]">
            1) On the laptop, open <b>trackside\demo\.env</b> and replace the BACKEND_URL, SESSION_ID, DEVICE_TOKEN and DEMO_ZONES lines with these (the token is shown only now):
          </p>
          <pre data-testid="laptop-link-env" className="p-2 rounded bg-[#0A0E13] border border-[#232B35] text-[10px] text-[#E7EDF3] whitespace-pre-wrap break-all">
            {envLines(link, showToken ? undefined : "dt_••••••••")}
          </pre>
          <div className="flex flex-wrap gap-2">
            <button data-testid="laptop-link-copy" onClick={copyLines} className={`${button} border-[#232B35] text-[#3FA6E0]`}>
              {copied ? "Copied" : "Copy lines"}
            </button>
            <button onClick={() => setShowToken((v) => !v)} className={`${button} border-[#232B35] text-[#7C8898]`}>
              {showToken ? "Hide token" : "Show token"}
            </button>
          </div>
          <p className="text-[11px] font-mono text-[#F2A93B]">
            2) Plug in the bridge, then in <b>trackside\demo</b> run: <b>py virtual_lap_simulator.py --post-batch 4 --laps 5</b>
          </p>
        </div>
      )}

      {active && (
        <div className="flex flex-wrap gap-2">
          {status.driver_id && (
            <button data-testid="laptop-link-watch" onClick={() => onWatchLive(status.driver_id as string)} className={`${button} border-[#232B35] text-[#3FA6E0]`}>
              <Eye size={13} /> Watch live
            </button>
          )}
          <button data-testid="laptop-link-stop" disabled={busy} onClick={stop} className={`${button} border-[#E5473C] text-[#E5473C]`}>
            <Square size={13} /> End link
          </button>
        </div>
      )}

      {error && <p data-testid="laptop-link-error" role="alert" className="text-[11px] text-[#E5473C]">{error}</p>}
    </div>
  );
}
