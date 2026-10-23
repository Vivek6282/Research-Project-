/**
 * Trackside Maps — "Draw on map" wizard: click points around a track on a real map, preview the smooth track and
 * its corners, name the corners, set their limits, and save. Saved maps work like any other map: the corner
 * editor, the live track view and Play demo all use them.
 */

import { lazy, Suspense, useState } from "react";
import { Crosshair, Eraser, Navigation, Undo2, X } from "lucide-react";
import { parseCoordinates } from "../../../lib/coordinates";
import { MAX_DRAWN_POINTS, MIN_DRAWN_POINTS, useDrawWizard } from "../hooks/use-draw-wizard";
import type { MapFocus } from "./draw-map-canvas";
import { WizardReview } from "./wizard-review";

// Leaflet is loaded only when this wizard is opened
const DrawMapCanvas = lazy(() => import("./draw-map-canvas"));

interface DrawMapWizardProps {
  onClose: () => void;
  onSaved: () => void;
}

const buttonClass =
  "text-xs font-mono px-3 py-2 min-h-[36px] rounded-[2px] cursor-pointer transition-colors disabled:opacity-50 disabled:cursor-not-allowed";
const toolClass = `${buttonClass} border border-[#232B35] text-[#E7EDF3] inline-flex items-center gap-1.5`;

/** The two-step modal: draw the track, then review and save. */
export function DrawMapWizard({ onClose, onSaved }: DrawMapWizardProps) {
  const wizard = useDrawWizard(onSaved);
  const { preview } = wizard;
  const [focus, setFocus] = useState<MapFocus | null>(null);
  const [place, setPlace] = useState("");

  /** Move the map to where this device is (the browser asks permission first). */
  const goToMyLocation = () => {
    if (!navigator.geolocation) return wizard.setError("This browser cannot tell where you are. Type the coordinates instead.");
    navigator.geolocation.getCurrentPosition(
      (position) => setFocus({ lat: position.coords.latitude, lng: position.coords.longitude, seq: Date.now() }),
      () => wizard.setError("Could not get your location (permission refused?). Type the coordinates instead."),
      { timeout: 10_000 },
    );
  };

  /** Move the map to typed coordinates. */
  const goToTyped = () => {
    const found = parseCoordinates(place);
    if (!found) return wizard.setError('Type a place as "latitude, longitude", for example 10.0123, 76.4567.');
    wizard.setError(null);
    setFocus({ ...found, seq: Date.now() });
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-3 sm:p-4">
      <div
        data-testid="draw-map-wizard"
        className="w-full max-w-3xl max-h-[92vh] overflow-y-auto bg-[#12181F] border border-[#232B35] rounded-[4px] shadow-2xl text-[#E7EDF3]"
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#232B35] bg-[#161D26] sticky top-0 z-[1000]">
          <span className="text-xs font-bold uppercase tracking-wider">
            Draw track — {preview ? "step 2 of 2: review" : "step 1 of 2: draw"}
          </span>
          <button aria-label="Close" onClick={onClose} className="text-[#7C8898] hover:text-[#E7EDF3] cursor-pointer">
            <X size={16} />
          </button>
        </div>

        <div className="p-4 flex flex-col gap-4">
          {wizard.error && (
            <p data-testid="wizard-error" role="alert" className="text-xs text-[#E5473C] border border-[#E5473C]/40 rounded p-2">
              {wizard.error}
            </p>
          )}

          {!preview && (
            <div className="flex flex-col gap-3">
              <p className="text-xs text-[#7C8898] leading-relaxed">
                Zoom the map to your track, then click points around it in driving order: the first point is the
                start/finish line. Click at least {MIN_DRAWN_POINTS} points (more in the corners). Drag a point to move it.
                The track is closed back to the first point and smoothed when you press Preview; nothing is saved until the last step.
              </p>
              <div className="flex flex-wrap items-center gap-2">
                <button data-testid="draw-undo" onClick={wizard.undo} disabled={wizard.points.length === 0} className={toolClass}>
                  <Undo2 size={14} /> Undo
                </button>
                <button data-testid="draw-clear" onClick={wizard.clear} disabled={wizard.points.length === 0} className={toolClass}>
                  <Eraser size={14} /> Clear
                </button>
                <button data-testid="draw-locate" onClick={goToMyLocation} className={toolClass}>
                  <Crosshair size={14} /> My location
                </button>
                <input
                  data-testid="draw-place-input"
                  aria-label="Go to coordinates"
                  placeholder="lat, lng"
                  value={place}
                  onChange={(e) => setPlace(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") goToTyped(); }}
                  className="bg-[#0A0E13] border border-[#232B35] rounded-[2px] px-2 py-1.5 text-xs text-[#E7EDF3] w-36"
                />
                <button data-testid="draw-go" onClick={goToTyped} className={toolClass}>
                  <Navigation size={14} /> Go
                </button>
              </div>

              <Suspense fallback={<div className="h-[380px] flex items-center justify-center text-[10px] font-mono text-[#7C8898] border border-[#232B35]">Loading map…</div>}>
                <DrawMapCanvas points={wizard.points} onAdd={wizard.addPoint} onMove={wizard.movePoint} focus={focus} />
              </Suspense>

              <div className="flex flex-wrap items-end justify-between gap-3">
                <p data-testid="draw-count" className="text-[11px] font-mono text-[#7C8898]">
                  {wizard.points.length} point{wizard.points.length === 1 ? "" : "s"}
                  {wizard.points.length < MIN_DRAWN_POINTS ? ` (need at least ${MIN_DRAWN_POINTS})` : ""}
                  {wizard.points.length >= MAX_DRAWN_POINTS ? " (limit reached)" : ""}
                </p>
                <label className="flex flex-col gap-1 text-[11px] font-mono text-[#7C8898] max-w-[260px]">
                  Corner radius (m): bends tighter than this count as corners
                  <input
                    data-testid="draw-radius-input"
                    inputMode="decimal"
                    value={wizard.radius}
                    onChange={(e) => wizard.setRadius(e.target.value)}
                    className="bg-[#0A0E13] border border-[#232B35] rounded-[2px] px-2 py-1.5 text-xs text-[#E7EDF3]"
                  />
                </label>
                <button
                  data-testid="draw-preview-btn"
                  disabled={!wizard.canPreview || wizard.busy}
                  onClick={wizard.runPreview}
                  className={`${buttonClass} bg-[#3FA6E0] text-[#06121B] font-bold`}
                >
                  {wizard.busy ? "Building track…" : "Preview track"}
                </button>
              </div>
            </div>
          )}

          {preview && (
            <WizardReview
              preview={preview}
              summary={`${wizard.points.length} points clicked · track length ${preview.outline_length_m.toFixed(0)} m · ${preview.corners.length} corners at radius ${preview.corner_radius_m} m`}
              mapName={wizard.mapName}
              onMapName={wizard.setMapName}
              choices={wizard.choices}
              onChoice={wizard.changeChoice}
              blocker={wizard.blocker}
              busy={wizard.busy}
              backLabel="Back to drawing"
              onBack={wizard.backToDrawing}
              onSave={wizard.save}
              noCornersHint="No corners were found at this radius. Go back, raise the radius (or draw the corners tighter), and preview again."
            />
          )}
        </div>
      </div>
    </div>
  );
}
