/**
 * Trackside Coach — the "Maps & Demo" tab: the simulator's built-in map and every custom map as
 * cards, with Add track, Archived/Restore and (Coach only) the demo controls.
 */

import { Map as MapIcon } from "lucide-react";
import { Panel } from "../../../components/ui/panel";
import { MapsBrowser } from "../../maps/components/maps-browser";

/** The tab body. */
export function MapsDemoTab() {
  return (
    <main data-testid="coach-maps-demo-tab" className="max-w-[1400px] mx-auto px-2.5 sm:px-4 py-3 sm:py-4">
      <Panel title="Maps & Demo" icon={MapIcon}>
        <MapsBrowser canManage canEditCorners />
      </Panel>
    </main>
  );
}
