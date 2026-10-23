/**
 * Trackside Maps — the review step shared by the upload wizard and the drawing wizard:
 * the outline with its corners, the map name, the corner names and limits, and Save.
 */

import { CornerTable } from "./corner-table";
import { OutlineSvg } from "./outline-svg";
import type { CornerChoice, ImportPreview } from "../types";

interface WizardReviewProps {
  preview: ImportPreview;
  /** One line under the title: what was read or drawn */
  summary: string;
  mapName: string;
  onMapName: (name: string) => void;
  choices: CornerChoice[];
  onChoice: (number: number, patch: Partial<CornerChoice>) => void;
  blocker: string | null;
  busy: boolean;
  backLabel: string;
  onBack: () => void;
  onSave: () => void;
  /** What to do when no corners were found (shown when the corner list is empty) */
  noCornersHint: string;
}

const buttonClass =
  "text-xs font-mono px-3 py-2 min-h-[36px] rounded-[2px] cursor-pointer transition-colors disabled:opacity-50 disabled:cursor-not-allowed";

/** The review step. */
export function WizardReview({
  preview, summary, mapName, onMapName, choices, onChoice, blocker, busy, backLabel, onBack, onSave, noCornersHint,
}: WizardReviewProps) {
  return (
    <>
      <p className="text-xs font-mono text-[#7C8898]" data-testid="wizard-summary">{summary}</p>
      <OutlineSvg outline={preview.outline} corners={preview.corners} />
      <label className="flex flex-col gap-1 text-[11px] font-mono text-[#7C8898]">
        Map name
        <input
          data-testid="map-name-input"
          value={mapName}
          maxLength={150}
          onChange={(e) => onMapName(e.target.value)}
          className="bg-[#0A0E13] border border-[#232B35] rounded-[2px] px-2 py-1.5 text-xs text-[#E7EDF3]"
        />
      </label>
      {preview.corners.length === 0 ? (
        <p className="text-xs text-[#F2A93B]" data-testid="wizard-no-corners">{noCornersHint}</p>
      ) : (
        <CornerTable corners={preview.corners} choices={choices} range={preview.limit_range_g} onChange={onChoice} />
      )}
      {blocker && (
        <p data-testid="wizard-blocker" className="text-[11px] text-[#7C8898]">
          Cannot save yet: {blocker}
        </p>
      )}
      <div className="flex gap-2 justify-end">
        <button onClick={onBack} className={`${buttonClass} border border-[#232B35] text-[#7C8898]`}>
          {backLabel}
        </button>
        <button
          data-testid="map-save-btn"
          disabled={Boolean(blocker) || busy}
          onClick={onSave}
          className={`${buttonClass} bg-[#3FA6E0] text-[#06121B] font-bold`}
        >
          {busy ? "Saving…" : "Save map"}
        </button>
      </div>
    </>
  );
}
