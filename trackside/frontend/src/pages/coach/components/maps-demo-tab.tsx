/**
 * Trackside Coach — the "Maps & Demo" tab: the simulator's built-in map and every custom map as
 * cards, with Add track, corner editing, Archived/Restore and (Coach only) the demo controls.
 */

import { useState } from "react";
import { Map as MapIcon } from "lucide-react";
import { Panel } from "../../../components/ui/panel";
import { MapsBrowser } from "../../maps/components/maps-browser";
import { PlayDemoDialog, type PlayChoice } from "../../maps/components/play-demo-dialog";
import type { MapTrack } from "../../maps/types";
import { demoSwitchIsOn, useDemoRun } from "../hooks/use-demo-run";
import { DemoStatusPanel } from "./demo-status-panel";

interface MapsDemoTabProps {
  /** Switch to the Live Pit-Wall Console with this driver selected */
  onWatchLive: (driverId: string) => void;
}

/** The tab body. */
export function MapsDemoTab({ onWatchLive }: MapsDemoTabProps) {
  const demo = useDemoRun(demoSwitchIsOn());
  const [playing, setPlaying] = useState<MapTrack | null>(null);
  const canPlay = demo.availability === "available";

  /** Ask the server to start the run the coach set up in the dialog. */
  async function handleStart(choice: PlayChoice) {
    if (!playing) return false;
    return demo.start({ track_id: playing.id, driver_id: choice.driverId, laps: choice.laps, pace: choice.pace });
  }

  return (
    <main data-testid="coach-maps-demo-tab" className="max-w-[1400px] mx-auto px-2.5 sm:px-4 py-3 sm:py-4">
      <Panel title="Maps & Demo" icon={MapIcon}>
        <MapsBrowser
          canManage
          canEditCorners
          onPlay={canPlay ? setPlaying : undefined}
          playDisabledReason={demo.isRunning ? "A demo is already running. Stop it first." : null}
        >
          <DemoStatusPanel
            availability={demo.availability}
            status={demo.status}
            actionError={demo.actionError}
            onStop={demo.stop}
            onWatchLive={onWatchLive}
          />
        </MapsBrowser>
      </Panel>
      {playing && (
        <PlayDemoDialog map={playing} onClose={() => setPlaying(null)} onStart={handleStart} serverError={demo.actionError} />
      )}
    </main>
  );
}
